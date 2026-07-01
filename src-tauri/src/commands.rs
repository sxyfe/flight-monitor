use serde::Serialize;
use tauri::State;

use crate::credentials::{
    delete_api_key, delete_webhook_url, get_api_key, get_webhook_url, save_api_key, save_webhook_url,
};
use crate::db::repository::{
    get_monitor_rule, get_notification_log, get_price_history, is_onboarding_complete,
    save_monitor_rule, set_onboarding_complete, MonitorRule, MonitorRuleInput,
    NotificationLogItem, PriceHistoryItem,
};
use crate::error::AppResult;
use crate::polling::engine::{get_poll_status, run_poll_cycle, PollStatus, AppState};
use crate::rollinggo::client::RollingGoClient;
use crate::rollinggo::types::AirportInfo;
use crate::notification::feishu::send_test_message;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AppBootstrapState {
    pub onboarding_complete: bool,
    pub has_api_key: bool,
    pub has_webhook: bool,
    pub has_monitor: bool,
}

#[tauri::command]
pub fn get_app_state(state: State<'_, AppState>) -> AppResult<AppBootstrapState> {
    Ok(AppBootstrapState {
        onboarding_complete: is_onboarding_complete(&state.db)?,
        has_api_key: get_api_key()?.is_some(),
        has_webhook: get_webhook_url()?.is_some(),
        has_monitor: get_monitor_rule(&state.db)?.is_some(),
    })
}

#[tauri::command]
pub fn save_api_key_command(key: String) -> AppResult<()> {
    save_api_key(&key)
}

#[tauri::command]
pub fn clear_api_key_command() -> AppResult<()> {
    delete_api_key()
}

#[tauri::command]
pub async fn validate_api_key_command(key: Option<String>) -> AppResult<()> {
    let api_key = match key {
        Some(value) if !value.trim().is_empty() => value,
        _ => crate::credentials::require_api_key()?,
    };
    RollingGoClient::new(api_key)?.validate_key().await
}

#[tauri::command]
pub fn save_webhook_command(url: String) -> AppResult<()> {
    save_webhook_url(&url)
}

#[tauri::command]
pub fn clear_webhook_command() -> AppResult<()> {
    delete_webhook_url()
}

#[tauri::command]
pub async fn test_webhook_command(url: Option<String>) -> AppResult<()> {
    let webhook = match url {
        Some(value) if !value.trim().is_empty() => value,
        _ => crate::credentials::require_webhook_url()?,
    };
    send_test_message(&webhook).await
}

#[tauri::command]
pub fn complete_onboarding_command(state: State<'_, AppState>) -> AppResult<()> {
    set_onboarding_complete(&state.db)
}

#[tauri::command]
pub fn get_monitor_rule_command(state: State<'_, AppState>) -> AppResult<Option<MonitorRule>> {
    get_monitor_rule(&state.db)
}

#[tauri::command]
pub fn save_monitor_rule_command(
    state: State<'_, AppState>,
    rule: MonitorRuleInput,
) -> AppResult<MonitorRule> {
    save_monitor_rule(&state.db, rule)
}

#[tauri::command]
pub fn get_poll_status_command(state: State<'_, AppState>) -> AppResult<PollStatus> {
    get_poll_status(&state)
}

#[tauri::command]
pub async fn trigger_poll_now_command(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> AppResult<PollStatus> {
    run_poll_cycle(&app, &state).await?;
    get_poll_status(&state)
}

#[tauri::command]
pub fn get_price_history_command(
    state: State<'_, AppState>,
    limit: Option<i64>,
) -> AppResult<Vec<PriceHistoryItem>> {
    get_price_history(&state.db, limit.unwrap_or(30))
}

#[tauri::command]
pub fn get_notification_log_command(
    state: State<'_, AppState>,
    limit: Option<i64>,
) -> AppResult<Vec<NotificationLogItem>> {
    get_notification_log(&state.db, limit.unwrap_or(30))
}

#[tauri::command]
pub async fn search_airports_command(keyword: String) -> AppResult<Vec<AirportInfo>> {
    let api_key = crate::credentials::require_api_key()?;
    let response = RollingGoClient::new(api_key)?
        .search_airports(&keyword)
        .await?;
    Ok(response.air_port_information_list)
}

#[tauri::command]
pub fn mask_secret_command() -> AppResult<Option<String>> {
    Ok(get_api_key()?.map(|_| "••••••••".into()))
}

#[tauri::command]
pub fn mask_webhook_command() -> AppResult<Option<String>> {
    Ok(get_webhook_url()?.map(|value| {
        if value.len() <= 12 {
            "••••••••".into()
        } else {
            format!("{}...{}", &value[..8], &value[value.len() - 4..])
        }
    }))
}
