use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    App, Emitter, Manager,
};

use crate::sidecar::SidecarState;

pub fn setup_tray(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let show_item = MenuItem::with_id(app, "show", "Open YT Booster", true, None::<&str>)?;
    let status_item = MenuItem::with_id(app, "status", "● Engine Running", false, None::<&str>)?;
    let separator1 = MenuItem::with_id(app, "sep1", "─────────────", false, None::<&str>)?;
    let start_item = MenuItem::with_id(app, "start_engine", "▶  Start Engine", true, None::<&str>)?;
    let stop_item = MenuItem::with_id(app, "stop_engine", "⏹  Stop Engine", true, None::<&str>)?;
    let separator2 = MenuItem::with_id(app, "sep2", "─────────────", false, None::<&str>)?;
    let settings_item = MenuItem::with_id(app, "settings", "⚙  Settings", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "✕  Quit", true, None::<&str>)?;

    let menu = Menu::with_items(
        app,
        &[
            &show_item,
            &status_item,
            &separator1,
            &start_item,
            &stop_item,
            &separator2,
            &settings_item,
            &quit_item,
        ],
    )?;

    TrayIconBuilder::with_id("main-tray")
        .icon(app.default_window_icon().cloned().unwrap())
        .menu(&menu)
        .tooltip("YT Booster")
        .on_menu_event(move |app, event| {
            match event.id.as_ref() {
                "show" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "start_engine" => {
                    let app_handle = app.clone();
                    let state = app.state::<SidecarState>().inner().clone();
                    tauri::async_runtime::spawn(async move {
                        let _ = crate::sidecar::start_engine(&app_handle, &state).await;
                    });
                }
                "stop_engine" => {
                    let app_handle = app.clone();
                    let state = app.state::<SidecarState>().inner().clone();
                    tauri::async_runtime::spawn(async move {
                        let _ = crate::sidecar::stop_engine(&app_handle, &state).await;
                    });
                }
                "settings" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                        let _ = window.emit("navigate", "settings");
                    }
                }
                "quit" => {
                    // Stop engine before quitting
                    let app_handle = app.clone();
                    let state = app.state::<SidecarState>().inner().clone();
                    let app_clone = app.clone();
                    tauri::async_runtime::spawn(async move {
                        let _ = crate::sidecar::stop_engine(&app_handle, &state).await;
                        app_clone.exit(0);
                    });
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let tauri::tray::TrayIconEvent::DoubleClick { .. } = event {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}
