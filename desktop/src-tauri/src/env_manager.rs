use std::collections::HashMap;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use tauri::AppHandle;
use crate::sidecar::find_dev_python_dir;

/// Get the path to the .env file
pub fn get_env_file_path(app_handle: &AppHandle) -> Result<PathBuf, String> {
    use tauri::Manager;

    // 1. Check development directory
    if let Some(py_dir) = find_dev_python_dir() {
        let dev_env = py_dir.join(".env");
        if dev_env.exists() {
            println!("[EnvManager] Using dev .env: {}", dev_env.display());
            return Ok(dev_env);
        }
        let dev_example = py_dir.join(".env.example");
        if dev_example.exists() {
            let _ = fs::copy(&dev_example, &dev_env);
            println!("[EnvManager] Initialized dev .env from example: {}", dev_env.display());
            return Ok(dev_env);
        }
    }

    // 2. Production: Always use user-specific app config directory (writable without admin rights)
    let config_dir = app_handle
        .path()
        .app_config_dir()
        .or_else(|_| app_handle.path().app_data_dir())
        .map_err(|e| format!("Failed to get user config dir: {}", e))?;

    let _ = fs::create_dir_all(&config_dir);
    let user_env = config_dir.join(".env");
    println!("[EnvManager] Using user config .env path: {}", user_env.display());

    if !user_env.exists() {
        // Try copying from bundled resource .env.example
        let mut copied = false;
        if let Ok(resource_dir) = app_handle.path().resource_dir() {
            let prod_example = resource_dir.join("resources/.env.example");
            if prod_example.exists() {
                if fs::copy(&prod_example, &user_env).is_ok() {
                    copied = true;
                }
            }
        }
        if !copied {
            let default_content = "# YT Booster Node Configuration\nPORT=8008\nLARAVEL_API_URL=http://127.0.0.1:8000/api\nLARAVEL_API_TOKEN=\nSAAS_DEVICE_KEY=\nNGROK_AUTHTOKEN=\nNGROK_DOMAIN=\nDEBUG=True\n";
            let _ = fs::write(&user_env, default_content);
        }
    }

    Ok(user_env)
}

/// Read and parse the .env file into a HashMap
pub fn read_env_file(app_handle: &AppHandle) -> Result<HashMap<String, String>, String> {
    let env_path = get_env_file_path(app_handle)?;
    if !env_path.exists() {
        return Ok(HashMap::new());
    }

    let file = fs::File::open(&env_path).map_err(|e| format!("Failed to open .env: {}", e))?;
    let reader = BufReader::new(file);

    let mut settings = HashMap::new();

    for line in reader.lines() {
        let line = line.map_err(|e| format!("Failed to read line: {}", e))?;
        let trimmed = line.trim();

        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        if let Some(eq_pos) = trimmed.find('=') {
            let key = trimmed[..eq_pos].trim().to_string();
            let value = trimmed[eq_pos + 1..].trim().to_string();

            let value = if (value.starts_with('"') && value.ends_with('"'))
                || (value.starts_with('\'') && value.ends_with('\''))
            {
                value[1..value.len() - 1].to_string()
            } else {
                value
            };

            settings.insert(key, value);
        }
    }

    Ok(settings)
}

/// Write settings back to the .env file, preserving comments and structure
pub fn write_env_file(app_handle: &AppHandle, settings: &HashMap<String, String>) -> Result<(), String> {
    let env_path = get_env_file_path(app_handle)?;
    
    let mut output_lines: Vec<String> = Vec::new();
    let mut written_keys: std::collections::HashSet<String> = std::collections::HashSet::new();

    if env_path.exists() {
        let file = fs::File::open(&env_path).map_err(|e| format!("Failed to open .env: {}", e))?;
        let reader = BufReader::new(file);

        for line in reader.lines() {
            let line = line.map_err(|e| format!("Failed to read line: {}", e))?;
            let trimmed = line.trim();

            if trimmed.is_empty() || trimmed.starts_with('#') {
                output_lines.push(line);
                continue;
            }

            if let Some(eq_pos) = trimmed.find('=') {
                let key = trimmed[..eq_pos].trim();

                if let Some(new_value) = settings.get(key) {
                    output_lines.push(format!("{}={}", key, new_value));
                    written_keys.insert(key.to_string());
                } else {
                    output_lines.push(line);
                }
            } else {
                output_lines.push(line);
            }
        }
    }

    // Append new keys
    for (key, value) in settings {
        if !written_keys.contains(key) {
            output_lines.push(format!("{}={}", key, value));
        }
    }

    if let Some(parent) = env_path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let mut content = output_lines.join("\n");
    if !content.ends_with('\n') {
        content.push('\n');
    }

    fs::write(&env_path, content)
        .map_err(|e| format!("Failed to save .env to {}: {}", env_path.display(), e))?;

    Ok(())
}
