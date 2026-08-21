mod sidecar;
mod env_manager;
mod tray;

use sidecar::SidecarState;
use tauri::Manager;

/// Read the .env file and return as JSON object
#[tauri::command]
fn read_env(app_handle: tauri::AppHandle) -> Result<std::collections::HashMap<String, String>, String> {
    env_manager::read_env_file(&app_handle)
}

/// Write settings back to the .env file
#[tauri::command]
fn write_env(app_handle: tauri::AppHandle, settings: std::collections::HashMap<String, String>) -> Result<(), String> {
    env_manager::write_env_file(&app_handle, &settings)
}

/// Start the Python sidecar engine
#[tauri::command]
async fn start_engine(app_handle: tauri::AppHandle, state: tauri::State<'_, SidecarState>) -> Result<String, String> {
    sidecar::start_engine(&app_handle, &state).await
}

/// Stop the Python sidecar engine
#[tauri::command]
async fn stop_engine(app_handle: tauri::AppHandle, state: tauri::State<'_, SidecarState>) -> Result<String, String> {
    sidecar::stop_engine(&app_handle, &state).await
}

/// Get current engine status
#[tauri::command]
fn get_engine_status(state: tauri::State<'_, SidecarState>) -> serde_json::Value {
    sidecar::get_engine_status(&state)
}

/// Test connection to Laravel server
#[tauri::command]
async fn test_connection(url: String) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;
    
    let base_url = url.trim_end_matches('/').to_string();
    let health_url = format!("{}/health", base_url);
    
    // First try /health
    if let Ok(resp) = client.get(&health_url).send().await {
        let status = resp.status().as_u16();
        if status >= 200 && status < 400 {
            return Ok(serde_json::json!({
                "success": true,
                "status_code": status,
                "url": health_url
            }));
        }
    }

    // Fallback: try base url
    match client.get(&base_url).send().await {
        Ok(resp) => {
            let status = resp.status().as_u16();
            // Any response code except 502/503/504 means the web server is online
            let success = status != 502 && status != 503 && status != 504;
            Ok(serde_json::json!({
                "success": success,
                "status_code": status,
                "url": base_url
            }))
        }
        Err(e) => {
            Ok(serde_json::json!({
                "success": false,
                "error": e.to_string(),
                "url": base_url
            }))
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .manage(SidecarState::new())
        .setup(|app| {
            // Setup system tray
            tray::setup_tray(app)?;

            // Auto-start the engine on app launch
            let app_handle = app.handle().clone();
            let state = app.state::<SidecarState>().inner().clone();
            tauri::async_runtime::spawn(async move {
                match sidecar::start_engine(&app_handle, &state).await {
                    Ok(msg) => println!("[YT Booster] Engine started: {}", msg),
                    Err(e) => eprintln!("[YT Booster] Failed to auto-start engine: {}", e),
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            // Minimize to tray instead of closing
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            start_engine,
            stop_engine,
            get_engine_status,
            read_env,
            write_env,
            test_connection,
        ])
        .run(tauri::generate_context!())
        .expect("error while running YT Booster");
}
