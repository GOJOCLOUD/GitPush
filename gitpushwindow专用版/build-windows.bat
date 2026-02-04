@echo off
echo ========================================
echo GitPush Windows Build Script
echo ========================================
echo.

REM 检查是否安装了必要的工具
where pnpm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] pnpm is not installed. Please install pnpm first.
    echo You can install it with: npm install -g pnpm
    pause
    exit /b 1
)

where cargo >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Rust/Cargo is not installed. Please install Rust first.
    echo You can download it from: https://rustup.rs/
    pause
    exit /b 1
)

echo [INFO] Cleaning previous builds...
if exist "frontend\dist" rmdir /s /q "frontend\dist"
if exist "frontend\src-tauri\target" rmdir /s /q "frontend\src-tauri\target"

echo [INFO] Installing frontend dependencies...
cd frontend
pnpm install

echo [INFO] Building frontend...
pnpm build

echo [INFO] Building Windows application...
pnpm tauri:build

echo.
echo ========================================
echo [SUCCESS] Build completed!
echo You can find the installer in:
echo frontend\src-tauri\target\release\bundle\
echo ========================================
pause