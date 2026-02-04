import subprocess
import sys
import os
import time
from pathlib import Path

# --- 1. Basic Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# --- 3. Color Output Helper ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(msg, level="INFO"):
    """Colored log output"""
    if level == "INFO":
        print(f"{Colors.GREEN}[INFO] {msg}{Colors.ENDC}")
    elif level == "WARN":
        print(f"{Colors.WARNING}[WARN] {msg}{Colors.ENDC}")
    elif level == "ERROR":
        print(f"{Colors.FAIL}[ERROR] {msg}{Colors.ENDC}")
    elif level == "HEADER":
        print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")

def start_backend():
    log(f"Starting Backend (FastAPI) | Path: {BACKEND_DIR}", "INFO")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR,
        shell=False
    )

def start_vite():
    log(f"Starting Vite Dev Server | Path: {FRONTEND_DIR}", "INFO")
    return subprocess.Popen(
        ["pnpm", "vite"],
        cwd=FRONTEND_DIR,
        shell=False
    )

def start_tauri():
    log(f"Starting Tauri Desktop App | Path: {FRONTEND_DIR}", "INFO")
    cmd = ["pnpm", "tauri", "dev"]
    return subprocess.Popen(
        cmd,
        cwd=FRONTEND_DIR,
        shell=False
    )

def main():
    print("=" * 60)
    log("GitPush V3 Development Launcher", "HEADER")
    print(f"Project Root: {ROOT_DIR}")
    print("=" * 60)
    
    # Path validation
    if not BACKEND_DIR.exists() or not FRONTEND_DIR.exists():
        log(f"Directories missing!\nBackend: {BACKEND_DIR}\nFrontend: {FRONTEND_DIR}", "ERROR")
        sys.exit(1)

    backend_process = None
    vite_process = None
    tauri_process = None

    try:
        # 1. Start services in dependency order
        backend_process = start_backend()
        
        # Wait for backend initialization
        time.sleep(2)
        
        # Start Vite dev server
        vite_process = start_vite()
        
        # Wait for Vite to be ready
        log("Waiting for Vite dev server to start...", "INFO")
        time.sleep(5)
        
        # Start Tauri desktop app
        tauri_process = start_tauri()
        
        log("All services ready. Logs will appear below.", "INFO")
        log("Press Ctrl+C to stop all services", "WARN")
        print("-" * 60)
        
        # 2. Core: Non-blocking polling
        while True:
            # poll() returns None if process is running, exit code otherwise
            backend_status = backend_process.poll()
            vite_status = vite_process.poll()
            tauri_status = tauri_process.poll()
            
            # Exit if any process terminates
            if backend_status is not None:
                log(f"Backend exited unexpectedly (Exit Code: {backend_status})", "ERROR")
                break
            if vite_status is not None:
                log(f"Vite exited unexpectedly (Exit Code: {vite_status})", "ERROR")
                break
            if tauri_status is not None:
                log(f"Tauri exited unexpectedly (Exit Code: {tauri_status})", "ERROR")
                break
            
            # Reduce CPU usage
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n")
        log("Received stop signal, cleaning up...", "WARN")
    except Exception as e:
        log(f"Unknown error occurred: {e}", "ERROR")
    finally:
        # 3. Core: Robust process termination
        # Terminate in logical dependency order: tauri -> vite -> backend
        for name, proc in [("Tauri", tauri_process), ("Vite", vite_process), ("Backend", backend_process)]:
            if proc and proc.poll() is None: # Only kill if process is still running
                print(f"Stopping {name}...", end=" ", flush=True)
                try:
                    proc.terminate() # Graceful shutdown: send SIGTERM
                    proc.wait(timeout=3) # Wait 3 seconds
                    print(f"{Colors.GREEN}Success{Colors.ENDC}")
                except subprocess.TimeoutExpired:
                    print(f"{Colors.FAIL}Timeout, force killing{Colors.ENDC}")
                    try:
                        proc.kill() # Force kill: send SIGKILL
                    except:
                        pass
                except Exception as e:
                    print(f"Failed: {e}")
        
        log("All services stopped.", "HEADER")

if __name__ == "__main__":
    main()