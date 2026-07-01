use std::sync::Mutex;

use chrono::{DateTime, Utc};
use serde::Serialize;
use tauri::{AppHandle, Emitter};

use crate::credentials::{get_api_key, get_webhook_url, require_api_key, require_webhook_url};
use crate::db::repository::{
    get_monitor_rule, get_notification_state, insert_notification_log, insert_price_history,
    is_onboarding_complete, upsert_notification_state,
};
use crate::db::DbState;
use crate::error::{AppError, AppResult};
use crate::notification::evaluator::should_notify;
use crate::notification::feishu::send_price_alert;
use crate::rollinggo::client::RollingGoClient;
use crate::rollinggo::quote::quote_rule;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PollStatus {
    pub running: bool,
    pub last_polled_at: Option<String>,
    pub next_poll_at: Option<String>,
    pub last_combined_total: Option<f64>,
    pub last_error: Option<String>,
    pub polling: bool,
}

#[derive(Default)]
pub struct PollRuntimeState {
    pub last_polled_at: Option<DateTime<Utc>>,
    pub next_poll_at: Option<DateTime<Utc>>,
    pub last_combined_total: Option<f64>,
    pub last_error: Option<String>,
    pub polling: bool,
}

pub struct AppState {
    pub db: DbState,
    pub poll_runtime: Mutex<PollRuntimeState>,
}

pub async fn run_poll_cycle(app: &AppHandle, state: &AppState) -> AppResult<()> {
    {
        let mut runtime = state.poll_runtime.lock().map_err(|_| {
            AppError::Internal("poll runtime lock poisoned".into())
        })?;
        runtime.polling = true;
        runtime.last_error = None;
    }

    let result = execute_poll(app, state).await;

    {
        let mut runtime = state.poll_runtime.lock().map_err(|_| {
            AppError::Internal("poll runtime lock poisoned".into())
        })?;
        runtime.polling = false;
        runtime.last_polled_at = Some(Utc::now());
        runtime.next_poll_at = Some(Utc::now() + chrono::Duration::hours(1));
        if let Err(err) = &result {
            runtime.last_error = Some(err.to_string());
        }
    }

    let _ = app.emit("poll-updated", get_poll_status(state)?);
    result
}

async fn execute_poll(app: &AppHandle, state: &AppState) -> AppResult<()> {
    if !is_onboarding_complete(&state.db)? {
        return Ok(());
    }

    let rule = match get_monitor_rule(&state.db)? {
        Some(rule) => rule,
        None => return Ok(()),
    };

    let api_key = require_api_key()?;
    let client = RollingGoClient::new(api_key)?;

    let quote = match quote_rule(&client, &rule).await {
        Ok(quote) => quote,
        Err(err) => {
            insert_price_history(&state.db, None, false, Some(&err.to_string()), None)?;
            return Err(err);
        }
    };

    let segments_json = serde_json::to_string(&quote.segments)?;
    insert_price_history(
        &state.db,
        Some(quote.combined_total),
        true,
        None,
        Some(&segments_json),
    )?;

    {
        let mut runtime = state.poll_runtime.lock().map_err(|_| {
            AppError::Internal("poll runtime lock poisoned".into())
        })?;
        runtime.last_combined_total = Some(quote.combined_total);
    }

    let mut notify_state = get_notification_state(&state.db)?;
    notify_state.last_total_price = Some(quote.combined_total);

    if should_notify(&notify_state, quote.combined_total, rule.max_price) {
        let webhook = require_webhook_url()?;
        match send_price_alert(&webhook, &rule.name, &quote, rule.max_price).await {
            Ok(message) => {
                insert_notification_log(&state.db, quote.combined_total, true, &message)?;
                notify_state.last_notified_price = Some(quote.combined_total);
                notify_state.last_notified_at = Some(Utc::now());
                let _ = app.emit("notification-sent", ());
            }
            Err(err) => {
                insert_notification_log(&state.db, quote.combined_total, false, &err.to_string())?;
                return Err(err);
            }
        }
    }

    upsert_notification_state(
        &state.db,
        notify_state.last_notified_price,
        notify_state.last_notified_at,
        notify_state.last_total_price,
    )?;

    Ok(())
}

pub fn get_poll_status(state: &AppState) -> AppResult<PollStatus> {
    let runtime = state
        .poll_runtime
        .lock()
        .map_err(|_| AppError::Internal("poll runtime lock poisoned".into()))?;

    Ok(PollStatus {
        running: get_api_key()?.is_some() && get_webhook_url()?.is_some(),
        last_polled_at: runtime.last_polled_at.map(|value| value.to_rfc3339()),
        next_poll_at: runtime.next_poll_at.map(|value| value.to_rfc3339()),
        last_combined_total: runtime.last_combined_total,
        last_error: runtime.last_error.clone(),
        polling: runtime.polling,
    })
}

pub fn can_poll(state: &AppState) -> AppResult<bool> {
    Ok(is_onboarding_complete(&state.db)?
        && get_monitor_rule(&state.db)?.is_some()
        && get_api_key()?.is_some()
        && get_webhook_url()?.is_some())
}
