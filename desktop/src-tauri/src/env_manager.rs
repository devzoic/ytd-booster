use std::collections::HashMap;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use tauri::AppHandle;
use crate::sidecar::find_dev_python_dir;

/// Get the path to the .env file
fn get_env_file_path(app_handle: &AppHandle) -> Result<PathBuf, String> {
    use tauri::Manager;

    // 1. Check development directory
    if let Some(py_dir) = find_dev_python_dir() {
        let dev_env = py_dir.join(".env");
        if dev_env.exists() {
            return Ok(dev_env);
        }
        let dev_example = py_dir.join(".env.example");
        if dev_example.exists() {
            let _ = fs::copy(&dev_example, &dev_env);
            return Ok(dev_env);
        }
    }

    // 2. Production resource directory
    let resource_dir = app_handle
        .path()
        .resource_dir()
        .map_err(|e| format!("Failed to get resource dir: {}", e))?;

    let prod_env = resource_dir.join(".env");
    if prod_env.exists() {
        return Ok(prod_env);
    }

    let prod_example = resource_dir.join("resources/.env.example");
    if prod_example.exists() {
        let _ = fs::copy(&prod_example, &prod_env);
        return Ok(prod_env);
    }

    // 3. Fallback: adjacent to executable
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let exe_env = parent.join(".env");
            if exe_env.exists() {
                return Ok(exe_env);
            }
        }
    }

    Ok(prod_env)
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

    // Write atomically
    let tmp_path = env_path.with_extension("env.tmp");
    let mut tmp_file = fs::File::create(&tmp_path)
        .map_err(|e| format!("Failed to create temp file: {}", e))?;

    for line in &output_lines {
        writeln!(tmp_file, "{}", line).map_err(|e| format!("Failed to write: {}", e))?;
    }

    tmp_file.flush().map_err(|e| format!("Failed to flush: {}", e))?;
    drop(tmp_file);

    fs::rename(&tmp_path, &env_path)
        .map_err(|e| format!("Failed to save .env: {}", e))?;

    Ok(())
}
