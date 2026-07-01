use std::time::Duration;

use tauri::{AppHandle, Manager};

use crate::polling::engine::{can_poll, run_poll_cycle, AppState};

pub fn start_scheduler(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(Duration::from_secs(30)).await;

        loop {
            if let Some(state) = app.try_state::<AppState>() {
                if can_poll(&state).unwrap_or(false) {
                    let _ = run_poll_cycle(&app, &state).await;
                }
            }

            tokio::time::sleep(Duration::from_secs(3600)).await;
        }
    });
}
