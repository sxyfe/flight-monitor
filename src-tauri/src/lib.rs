mod commands;
mod credentials;
mod db;
mod error;
mod notification;
mod polling;
mod rollinggo;

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Manager, WindowEvent};

use polling::engine::AppState;
use polling::scheduler::start_scheduler;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![]),
        ))
        .setup(|app| {
            let db = db::DbState::init(app.handle())?;
            app.manage(AppState {
                db,
                poll_runtime: std::sync::Mutex::new(polling::engine::PollRuntimeState::default()),
            });

            let show_item = MenuItem::with_id(app, "show", "显示窗口", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("Flight Monitor")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            if let Some(window) = app.get_webview_window("main") {
                let window_clone = window.clone();
                window.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = window_clone.hide();
                    }
                });
            }

            start_scheduler(app.handle().clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_app_state,
            commands::save_api_key_command,
            commands::clear_api_key_command,
            commands::validate_api_key_command,
            commands::save_webhook_command,
            commands::clear_webhook_command,
            commands::test_webhook_command,
            commands::complete_onboarding_command,
            commands::get_monitor_rule_command,
            commands::save_monitor_rule_command,
            commands::get_poll_status_command,
            commands::trigger_poll_now_command,
            commands::get_price_history_command,
            commands::get_notification_log_command,
            commands::search_airports_command,
            commands::mask_secret_command,
            commands::mask_webhook_command,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
