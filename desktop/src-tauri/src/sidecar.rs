use std::path::PathBuf;
use std::process::Command as StdCommand;
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Emitter, Manager};
use serde_json;

/// Shared state for managing the sidecar Python engine process
#[derive(Clone)]
pub struct SidecarState {
    /// PID of the running Python engine process
    pid: Arc<Mutex<Option<u32>>>,
    /// Whether the engine is currently running
    running: Arc<Mutex<bool>>,
}

impl SidecarState {
    pub fn new() -> Self {
        Self {
            pid: Arc::new(Mutex::new(None)),
            running: Arc::new(Mutex::new(false)),
        }
    }
}

/// Find repository python/ directory if running in development mode
pub fn find_dev_python_dir() -> Option<PathBuf> {
    let cwd = std::env::current_dir().unwrap_or_default();
    let candidates = vec![
        cwd.clone(),
        cwd.join("python"),
        cwd.join("../python"),
        cwd.join("../../python"),
        cwd.join("../../../python"),
    ];

    for c in candidates {
        if c.join("run.py").exists() {
            if let Ok(canonical) = c.canonicalize() {
                return Some(canonical);
            }
            return Some(c);
        }
    }

    // Also check relative to current exe
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let exe_candidates = vec![
                parent.join("../../../python"),
                parent.join("../../../../python"),
                parent.join("../../../../../python"),
            ];
            for c in exe_candidates {
                if c.join("run.py").exists() {
                    if let Ok(canonical) = c.canonicalize() {
                        return Some(canonical);
                    }
                    return Some(c);
                }
            }
        }
    }

    None
}

/// Locate the executable and working directory
pub fn get_engine_launch_target(app_handle: &AppHandle) -> Result<(PathBuf, Vec<String>, PathBuf), String> {
    let binary_name = if cfg!(target_os = "windows") {
        "yt-node.exe"
    } else {
        "yt-node"
    };

    // 1. Development mode: use python directory
    if let Some(py_dir) = find_dev_python_dir() {
        // Check if compiled binary exists in dist/ or desktop binaries/
        let dist_binary = py_dir.join("dist").join(binary_name);
        if dist_binary.exists() {
            return Ok((dist_binary, vec![], py_dir));
        }

        let sidecar_binary = py_dir.join("../desktop/src-tauri/binaries").join(binary_name);
        if sidecar_binary.exists() {
            return Ok((sidecar_binary, vec![], py_dir));
        }

        // Fallback in dev: run python directly
        let py_cmd = if cfg!(target_os = "windows") {
            let venv_py = py_dir.join("venv/Scripts/python.exe");
            if venv_py.exists() { venv_py.to_string_lossy().to_string() } else { "python".to_string() }
        } else {
            let venv_py = py_dir.join("venv/bin/python3");
            if venv_py.exists() { venv_py.to_string_lossy().to_string() } else { "python3".to_string() }
        };

        return Ok((PathBuf::from(py_cmd), vec!["run.py".to_string()], py_dir));
    }

    // 2. Production mode: check resource_dir and bundle paths
    let resource_dir = app_handle
        .path()
        .resource_dir()
        .map_err(|e| format!("Failed to get resource dir: {}", e))?;

    let candidates = vec![
        resource_dir.join(binary_name),
        resource_dir.join("binaries").join(binary_name),
    ];

    for path in candidates {
        if path.exists() {
            let work_dir = path.parent().unwrap_or(&resource_dir).to_path_buf();
            return Ok((path, vec![], work_dir));
        }
    }

    // 3. Fallback: adjacent to current executable
    if let Ok(exe_dir) = std::env::current_exe() {
        if let Some(parent) = exe_dir.parent() {
            let adjacent = parent.join(binary_name);
            if adjacent.exists() {
                return Ok((adjacent, vec![], parent.to_path_buf()));
            }
        }
    }

    Err(format!("Could not find '{}' binary or python environment", binary_name))
}

/// Start the Python sidecar engine
pub async fn start_engine(app_handle: &AppHandle, state: &SidecarState) -> Result<String, String> {
    {
        let running = state.running.lock().map_err(|e| e.to_string())?;
        if *running {
            return Ok("Engine is already running".to_string());
        }
    }

    let (cmd_path, args, work_dir) = get_engine_launch_target(app_handle)?;

    println!("[YT Booster] Spawning engine: {} {:?}", cmd_path.display(), args);
    println!("[YT Booster] Working directory: {}", work_dir.display());

    // Clean up any stale process holding the port from previous crashed runs
    #[cfg(unix)]
    {
        let _ = StdCommand::new("sh")
            .arg("-c")
            .arg("lsof -ti :8008 | xargs kill -9 2>/dev/null || true")
            .output();
        let _ = StdCommand::new("sh")
            .arg("-c")
            .arg("lsof -ti :8000 | xargs kill -9 2>/dev/null || true")
            .output();
    }

    let mut command = StdCommand::new(&cmd_path);
    command.args(&args);
    command.current_dir(&work_dir);
    command.env("TAURI_ENV", "1");

    // Inject all current .env settings into the child process environment
    if let Ok(env_path) = crate::env_manager::get_env_file_path(app_handle) {
        command.env("YT_ENV_FILE", &env_path);
        if let Some(parent) = env_path.parent() {
            command.env("YT_DATA_DIR", parent);
        }
    }
    if let Ok(env_vars) = crate::env_manager::read_env_file(app_handle) {
        for (k, v) in env_vars {
            if !k.is_empty() {
                command.env(&k, &v);
            }
        }
    }

    command.stdout(std::process::Stdio::piped());
    command.stderr(std::process::Stdio::piped());

    // Prevent cmd window on Windows
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let child = command.spawn().map_err(|e| format!("Failed to start engine: {}", e))?;
    let child_pid = child.id();

    {
        let mut pid = state.pid.lock().map_err(|e| e.to_string())?;
        *pid = Some(child_pid);
        let mut running = state.running.lock().map_err(|e| e.to_string())?;
        *running = true;
    }

    // Stream stdout/stderr to frontend via Tauri events
    let app_clone = app_handle.clone();
    let state_clone = state.clone();

    std::thread::spawn(move || {
        use std::io::{BufRead, BufReader};

        let stdout = child.stdout;
        let stderr = child.stderr;

        // Read stdout
        if let Some(stdout) = stdout {
            let app = app_clone.clone();
            std::thread::spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines() {
                    if let Ok(line) = line {
                        let level = if line.contains("ERROR") {
                            "error"
                        } else if line.contains("WARNING") {
                            "warning"
                        } else {
                            "info"
                        };
                        let _ = app.emit("engine-log", serde_json::json!({
                            "level": level,
                            "message": line,
                            "timestamp": chrono::Local::now().format("%H:%M:%S").to_string()
                        }));
                    }
                }
            });
        }

        // Read stderr
        if let Some(stderr) = stderr {
            let app = app_clone.clone();
            let reader = BufReader::new(stderr);
            for line in reader.lines() {
                if let Ok(line) = line {
                    let level = if line.contains("ERROR") || line.contains("error") {
                        "error"
                    } else if line.contains("WARNING") || line.contains("warning") {
                        "warning"
                    } else {
                        "info"
                    };
                    let _ = app.emit("engine-log", serde_json::json!({
                        "level": level,
                        "message": line,
                        "timestamp": chrono::Local::now().format("%H:%M:%S").to_string()
                    }));
                }
            }
        }

        // Process exited
        {
            if let Ok(mut running) = state_clone.running.lock() {
                *running = false;
            }
            if let Ok(mut pid) = state_clone.pid.lock() {
                *pid = None;
            }
        }
        let _ = app_clone.emit("engine-status", serde_json::json!({
            "running": false,
            "message": "Engine process exited"
        }));
    });

    let _ = app_handle.emit("engine-status", serde_json::json!({
        "running": true,
        "pid": child_pid,
        "message": "Engine started successfully"
    }));

    Ok(format!("Engine started (PID: {})", child_pid))
}

/// Stop the Python sidecar engine
pub async fn stop_engine(app_handle: &AppHandle, state: &SidecarState) -> Result<String, String> {
    let pid = {
        let pid_lock = state.pid.lock().map_err(|e| e.to_string())?;
        *pid_lock
    };

    let result = match pid {
        Some(pid) => {
            println!("[YT Booster] Stopping engine (PID: {})", pid);

            #[cfg(unix)]
            {
                use std::process::Command;
                // Kill child process tree first
                let _ = Command::new("pkill").arg("-P").arg(pid.to_string()).output();
                let _ = Command::new("kill").arg("-15").arg(pid.to_string()).output();
                tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                let _ = Command::new("kill").arg("-9").arg(pid.to_string()).output();
                let _ = Command::new("sh").arg("-c").arg("lsof -ti:8008,8000 | xargs kill -9 2>/dev/null || true").output();
                // Kill any active automation Chrome instances using profiles_data
                let _ = Command::new("sh").arg("-c").arg("ps aux | grep -i 'profiles_data' | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true").output();
            }

            #[cfg(windows)]
            {
                use std::process::Command;
                let _ = Command::new("taskkill")
                    .args(["/PID", &pid.to_string(), "/F", "/T"])
                    .output();
                let _ = Command::new("cmd")
                    .args(["/C", "wmic process where \"CommandLine like '%profiles_data%'\" call terminate >nul 2>&1"])
                    .output();
            }

            {
                let mut running = state.running.lock().map_err(|e| e.to_string())?;
                *running = false;
                let mut pid_lock = state.pid.lock().map_err(|e| e.to_string())?;
                *pid_lock = None;
            }

            Ok(format!("Engine stopped (PID: {})", pid))
        }
        None => {
            // Clean up any rogue processes holding ports
            #[cfg(unix)]
            {
                use std::process::Command;
                let _ = Command::new("sh").arg("-c").arg("lsof -ti:8008,8000 | xargs kill -9 2>/dev/null || true").output();
            }
            Ok("Engine was not running".to_string())
        }
    };

    let _ = app_handle.emit("engine-status", serde_json::json!({
        "running": false,
        "message": "Engine stopped"
    }));

    result
}

/// Get the current engine status
pub fn get_engine_status(state: &SidecarState) -> serde_json::Value {
    let running = state.running.lock().map(|r| *r).unwrap_or(false);
    let pid = state.pid.lock().map(|p| *p).unwrap_or(None);

    serde_json::json!({
        "running": running,
        "pid": pid
    })
}
