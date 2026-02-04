@echo off
setlocal enabledelayedexpansion

echo ========================================
echo GitPush Windows Enhanced Build Script
echo ========================================
echo.

REM 设置变量
set "MISSING_DEPS=0"
set "PYTHON_VERSION="
set "GIT_VERSION="
set "NODE_VERSION="
set "RUST_VERSION="

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 没有管理员权限，某些功能可能受限
    echo.
) else (
    echo [INFO] 检测到管理员权限
    echo.
)

REM 检查Node.js和npm
echo [INFO] 检查Node.js和npm...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js 未安装
    echo [INFO] 正在打开Node.js下载页面...
    start https://nodejs.org/en/download/
    set "MISSING_DEPS=1"
) else (
    for /f "tokens=*" %%i in ('node -v') do set "NODE_VERSION=%%i"
    echo [SUCCESS] Node.js 已安装: !NODE_VERSION!
    
    where npm >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] npm 未安装
        set "MISSING_DEPS=1"
    ) else (
        echo [SUCCESS] npm 已安装
    )
)

REM 检查pnpm
echo [INFO] 检查pnpm...
where pnpm >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] pnpm 未安装，正在尝试安装...
    npm install -g pnpm
    if %errorlevel% neq 0 (
        echo [ERROR] pnpm 安装失败
        set "MISSING_DEPS=1"
    ) else (
        echo [SUCCESS] pnpm 安装成功
    )
) else (
    echo [SUCCESS] pnpm 已安装
)

REM 检查Rust/Cargo
echo [INFO] 检查Rust/Cargo...
where cargo >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Rust/Cargo 未安装，正在尝试安装...
    echo [INFO] 正在下载rustup-init.exe...
    powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile 'rustup-init.exe'"
    if exist rustup-init.exe (
        echo [INFO] 正在安装Rust...
        rustup-init.exe -y --default-toolchain stable
        del rustup-init.exe
        refreshenv
        where cargo >nul 2>nul
        if %errorlevel% neq 0 (
            echo [ERROR] Rust/Cargo 安装失败，请手动安装
            echo [INFO] 请访问: https://rustup.rs/
            set "MISSING_DEPS=1"
        ) else (
            echo [SUCCESS] Rust/Cargo 安装成功
        )
    ) else (
        echo [ERROR] 无法下载rustup-init.exe
        set "MISSING_DEPS=1"
    )
) else (
    for /f "tokens=*" %%i in ('rustc -V') do set "RUST_VERSION=%%i"
    echo [SUCCESS] Rust/Cargo 已安装: !RUST_VERSION!
)

REM 检查Python
echo [INFO] 检查Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    where python3 >nul 2>nul
    if %errorlevel% neq 0 (
        echo [WARNING] Python 未安装，正在打开下载页面...
        start https://www.python.org/downloads/windows/
        echo [INFO] 请安装Python 3.8或更高版本
        set "MISSING_DEPS=1"
    ) else (
        for /f "tokens=*" %%i in ('python3 -V 2^>^&1') do set "PYTHON_VERSION=%%i"
        echo [SUCCESS] Python3 已安装: !PYTHON_VERSION!
    )
) else (
    for /f "tokens=*" %%i in ('python -V 2^>^&1') do set "PYTHON_VERSION=%%i"
    echo [SUCCESS] Python 已安装: !PYTHON_VERSION!
)

REM 检查Git
echo [INFO] 检查Git...
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Git 未安装，正在尝试安装...
    echo [INFO] 正在下载Git安装程序...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/latest/download/Git-2.43.0-64-bit.exe' -OutFile 'git-installer.exe'"
    if exist git-installer.exe (
        echo [INFO] 正在静默安装Git...
        git-installer.exe /VERYSILENT /NORESTART
        del git-installer.exe
        refreshenv
        where git >nul 2>nul
        if %errorlevel% neq 0 (
            echo [ERROR] Git 安装失败，请手动安装
            echo [INFO] 请访问: https://git-scm.com/download/win
            set "MISSING_DEPS=1"
        ) else (
            echo [SUCCESS] Git 安装成功
        )
    ) else (
        echo [ERROR] 无法下载Git安装程序
        set "MISSING_DEPS=1"
    )
) else (
    for /f "tokens=*" %%i in ('git --version') do set "GIT_VERSION=%%i"
    echo [SUCCESS] Git 已安装: !GIT_VERSION!
)

REM 检查Tauri所需的其他依赖
echo [INFO] 检查Tauri构建依赖...
where cargo >nul 2>nul
if %errorlevel% equ 0 (
    cargo tauri --version >nul 2>nul
    if %errorlevel% neq 0 (
        echo [INFO] 安装Tauri CLI...
        cargo install tauri-cli
    ) else (
        echo [SUCCESS] Tauri CLI 已安装
    )
)

REM 如果有缺失的依赖，询问是否继续
if %MISSING_DEPS% equ 1 (
    echo.
    echo [WARNING] 检测到缺失的依赖，某些功能可能无法正常工作
    set /p "CONTINUE=是否继续构建? (y/n): "
    if /i "!CONTINUE!" neq "y" (
        echo [INFO] 构建已取消
        pause
        exit /b 1
    )
)

REM 检查环境变量
echo [INFO] 检查环境变量...
echo [INFO] PATH: %PATH%

REM 清理之前的构建
echo.
echo [INFO] 清理之前的构建...
if exist "frontend\dist" (
    echo [INFO] 删除frontend\dist...
    rmdir /s /q "frontend\dist"
)
if exist "frontend\src-tauri\target" (
    echo [INFO] 删除frontend\src-tauri\target...
    rmdir /s /q "frontend\src-tauri\target"
)

REM 安装前端依赖
echo.
echo [INFO] 安装前端依赖...
cd frontend
pnpm install
if %errorlevel% neq 0 (
    echo [ERROR] 前端依赖安装失败
    pause
    exit /b 1
)

REM 构建前端
echo.
echo [INFO] 构建前端...
pnpm build
if %errorlevel% neq 0 (
    echo [ERROR] 前端构建失败
    pause
    exit /b 1
)

REM 构建Windows应用
echo.
echo [INFO] 构建Windows应用程序...
pnpm tauri:build
if %errorlevel% neq 0 (
    echo [ERROR] Windows应用构建失败
    pause
    exit /b 1
)

REM 构建完成
echo.
echo ========================================
echo [SUCCESS] 构建完成!
echo ========================================
echo.
echo 安装程序位置:
echo   - NSIS: frontend\src-tauri\target\release\bundle\nsis\
echo   - MSI:  frontend\src-tauri\target\release\bundle\msi\
echo.
echo 版本信息:
echo   - Node.js: !NODE_VERSION!
echo   - Rust:    !RUST_VERSION!
echo   - Python:  !PYTHON_VERSION!
echo   - Git:     !GIT_VERSION!
echo.
echo ========================================
pause