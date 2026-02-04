// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tauri::Manager;

#[cfg(windows)]
use winapi::um::processthreadsapi::{OpenProcess, TerminateProcess};
#[cfg(windows)]
use winapi::um::winnt::{PROCESS_TERMINATE, SYNCHRONIZE};
#[cfg(windows)]
use winapi::um::handleapi::CloseHandle;
#[cfg(windows)]
use std::os::raw::c_void;

mod commands;

struct FastAPIProcess(Arc<Mutex<Option<Child>>>);

/// 查找 Python 后端目录
/// 1. 开发模式: 从 src-tauri 往上找 backend 目录
/// 2. 打包模式: 从应用资源目录找 backend 目录
fn find_backend_dir(app_handle: &tauri::AppHandle) -> Option<PathBuf> {
    // 尝试方案1: 开发环境 - 从当前目录往上找
    if let Ok(current_dir) = std::env::current_dir() {
        // 尝试从 src-tauri 目录结构找
        let dev_backend = current_dir.parent()
            .and_then(|p| p.parent())
            .map(|p| p.join("backend"));
        
        if let Some(ref backend_dir) = dev_backend {
            let main_py = backend_dir.join("main.py");
            if main_py.exists() {
                println!("Found backend in dev mode: {:?}", backend_dir);
                return Some(backend_dir.clone());
            }
        }
        
        // 尝试从当前目录的 backend 子目录找
        let direct_backend = current_dir.join("backend");
        if direct_backend.join("main.py").exists() {
            println!("Found backend in current dir: {:?}", direct_backend);
            return Some(direct_backend);
        }
    }
    
    // 尝试方案2: 打包环境 - 从应用资源目录找
    if let Ok(resource_dir) = app_handle.path().resource_dir() {
        let resource_backend = resource_dir.join("backend");
        if resource_backend.join("main.py").exists() {
            println!("Found backend in resource dir: {:?}", resource_backend);
            return Some(resource_backend);
        }
    }
    
    // 尝试方案3: 从可执行文件位置找
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            // Windows: 与可执行文件同级目录
            let windows_backend = exe_dir.join("backend");
            if windows_backend.join("main.py").exists() {
                println!("Found backend in Windows: {:?}", windows_backend);
                return Some(windows_backend);
            }
            
            // 尝试可执行文件同级的 backend 目录
            let sibling_backend = exe_dir.join("backend");
            if sibling_backend.join("main.py").exists() {
                println!("Found backend next to exe: {:?}", sibling_backend);
                return Some(sibling_backend);
            }
        }
    }
    
    // 尝试方案4: 从用户主目录的固定位置找
    if let Some(home_dir) = dirs::home_dir() {
        let home_backend = home_dir.join(".gitpush").join("backend");
        if home_backend.join("main.py").exists() {
            println!("Found backend in home dir: {:?}", home_backend);
            return Some(home_backend);
        }
    }
    
    None
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(FastAPIProcess(Arc::new(Mutex::new(None))))
        .setup(|app| {
            let process_handle = app.state::<FastAPIProcess>();
            let process_handle = Arc::clone(&process_handle.0);
            let app_handle = app.handle().clone();
            
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
                
                let mut process_guard = process_handle.lock().unwrap();
                
                // 查找 Python 可执行文件 - Windows优先使用python命令
                let python_path = which::which("python")
                    .or_else(|_| which::which("python3"))
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_else(|_| "python".to_string());
                
                println!("Using Python: {}", python_path);
                
                // 查找后端目录
                let backend_dir = match find_backend_dir(&app_handle) {
                    Some(dir) => dir,
                    None => {
                        eprintln!("FastAPI backend not found in any expected location!");
                        eprintln!("Please ensure the backend directory is properly set up.");
                        eprintln!("Expected locations:");
                        eprintln!("  - Development: <project>\\backend\\main.py");
                        eprintln!("  - Production: %USERPROFILE%\\.gitpush\\backend\\main.py");
                        return;
                    }
                };
                
                let main_py = backend_dir.join("main.py");
                println!("Starting FastAPI backend from: {:?}", main_py);
                
                match Command::new(&python_path)
                    .arg(&main_py)
                    .current_dir(&backend_dir)
                    .spawn()
                {
                    Ok(child) => {
                        println!("FastAPI backend started with PID: {}", child.id());
                        *process_guard = Some(child);
                    }
                    Err(e) => {
                        eprintln!("Failed to start FastAPI backend: {}", e);
                        eprintln!("Python path: {}", python_path);
                        eprintln!("Backend dir: {:?}", backend_dir);
                    }
                }
            });
            
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let process_handle = window.state::<FastAPIProcess>();
                let mut process_guard = process_handle.0.lock().unwrap();
                
                if let Some(mut child) = process_guard.take() {
                    println!("Shutting down FastAPI backend with PID: {}", child.id());
                    
                    // Windows下使用Windows API终止进程
                    #[cfg(windows)]
                    {
                        let pid = child.id() as u32;
                        unsafe {
                            let process_handle = OpenProcess(PROCESS_TERMINATE | SYNCHRONIZE, 0, pid);
                            if !process_handle.is_null() {
                                let _ = TerminateProcess(process_handle, 1);
                                CloseHandle(process_handle);
                            }
                        }
                    }
                    
                    let _ = child.wait();
                    println!("FastAPI backend shutdown complete");
                }
            }
        })
        .invoke_handler(tauri::generate_handler![commands::greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
