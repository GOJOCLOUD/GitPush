// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tauri::Manager;

mod commands;

struct FastAPIProcess(Arc<Mutex<Option<Child>>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(FastAPIProcess(Arc::new(Mutex::new(None))))
        .setup(|app| {
            let process_handle = app.state::<FastAPIProcess>();
            let process_handle = Arc::clone(&process_handle.0);
            
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
                
                let mut process_guard = process_handle.lock().unwrap();
                
                let python_path = if cfg!(windows) {
                    "py"
                } else {
                    "python3"
                };
                
                let current_dir = std::env::current_dir().unwrap();
                let backend_dir = current_dir.parent().unwrap().parent().unwrap().join("backend");
                let main_py = backend_dir.join("main.py");
                
                if !main_py.exists() {
                    eprintln!("FastAPI backend not found at: {:?}", main_py);
                    eprintln!("Current directory: {:?}", current_dir);
                    return;
                }
                
                match Command::new(python_path)
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
                    
                    #[cfg(unix)]
                    {
                        use nix::sys::signal::{self, Signal};
                        use nix::unistd::Pid;
                        let _ = signal::kill(Pid::from_raw(child.id() as i32), Signal::SIGTERM);
                    }
                    
                    #[cfg(windows)]
                    {
                        let _ = child.kill();
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
