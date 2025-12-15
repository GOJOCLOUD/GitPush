use std::process::Command;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use tauri::ipc::InvokeError;

pub fn mask_token(token: &str) -> String {
    if token.len() > 8 {
        format!("{}***{}", &token[..4], &token[token.len() - 4..])
    } else if token.is_empty() {
        "".to_string()
    } else {
        "***".to_string()
    }
}

#[tauri::command]
pub fn run_python_upload(
    token: String,
    repo: String,
    branch: String,
    path: Vec<String>,
    action: String,
    proxy: Option<String>,
    ignore_patterns: Option<Vec<String>>,
) -> Result<serde_json::Value, InvokeError> {

    println!("\n=== PROCESS START ===");
    println!("Action: {}", action);
    println!("Token: {}", mask_token(&token));
    println!("Repo: {}", repo);
    println!("Branch: {}", branch);
    println!("Path(s): {:?}", path);
    println!("--------------------------");

    // 🚀 关键修复：强制 Python 在正确目录运行（防止污染 src-tauri）
    let python_cwd = "/Users/wutiaoyun/Desktop/gitpush/gitpush";

    // 创建 Command 对象并绑定到变量，确保更长的生命周期
    let mut command = Command::new("python3");
    command.current_dir(python_cwd);
    
    // 设置 PYTHONPATH 环境变量，确保能够找到 gitpush 模块
    command.env("PYTHONPATH", "/Users/wutiaoyun/Desktop/gitpush");
    
    if let Some(proxy_url) = proxy {
        if !proxy_url.trim().is_empty() {
            command.env("HTTP_PROXY", &proxy_url);
            command.env("HTTPS_PROXY", &proxy_url);
            println!("Proxy set for Python: {}", proxy_url);
        }
    }
    command.arg("backend_interface.py");
    command.arg("--token");
    command.arg(&token);
    command.arg("--repo");
    command.arg(&repo);
    command.arg("--action");
    command.arg(&action);

    // 根据 action 添加不同的参数
    if action == "upload" || action == "create_branch" {
        command.arg("--branch").arg(&branch);
    }
    
    if action == "upload" {
        // 为每个路径添加一个 --path 参数
        for p in &path {
            command.arg("--path").arg(p);
        }
        // 添加忽略模式
        if let Some(patterns) = ignore_patterns {
            for pat in patterns {
                if !pat.trim().is_empty() {
                    command.arg("--ignore").arg(pat);
                }
            }
        }
    }

    let output = command.output()
        .map_err(|e| {
            println!("ERROR: Failed to execute Python: {}", e);
            InvokeError::from(format!("Failed to execute Python: {}", e))
        })?;

    // Print Python output
    let stdout_str = String::from_utf8_lossy(&output.stdout);
    let stderr_str = String::from_utf8_lossy(&output.stderr);

    println!("\n---- PYTHON STDOUT ----");
    println!("{}", stdout_str);
    println!("\n---- PYTHON STDERR ----");
    println!("{}", stderr_str);
    println!("\n=== UPLOAD PROCESS END ===");

    // Python error handling
    if !output.status.success() {
        return Err(InvokeError::from(format!(
            "Python command failed: {}",
            stderr_str
        )));
    }

    if output.stdout.is_empty() {
        return Err(InvokeError::from("Python stdout is empty".to_string()));
    }

    // Parse JSON output
    let json: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|e| InvokeError::from(format!("Failed to parse JSON: {}", e)))?;

    Ok(json)
}

#[tauri::command]
pub fn write_text_file(
    filename: String,
    content: String,
    options: serde_json::Value,
) -> Result<(), InvokeError> {
    println!("\n=== WRITE TEXT FILE ===");
    println!("Filename: {}", filename);
    println!("Options: {:?}", options);
    
    // Determine the base directory
    let base_dir = match options.get("dir") {
        Some(serde_json::Value::String(dir)) => {
            match dir.as_str() {
                "home" => dirs::home_dir().ok_or(InvokeError::from("Home directory not found"))?,
                _ => dirs::home_dir().ok_or(InvokeError::from("Home directory not found"))?,
            }
        },
        _ => dirs::home_dir().ok_or(InvokeError::from("Home directory not found"))?,
    };
    
    // Create the full path
    let file_path = base_dir.join(filename);
    println!("Full path: {:?}", file_path);
    
    // Write the file
    let mut file = File::create(&file_path).map_err(|e| {
        InvokeError::from(format!("Failed to create file: {}", e))
    })?;
    
    file.write_all(content.as_bytes()).map_err(|e| {
        InvokeError::from(format!("Failed to write to file: {}", e))
    })?;
    
    println!("File written successfully");
    Ok(())
}
