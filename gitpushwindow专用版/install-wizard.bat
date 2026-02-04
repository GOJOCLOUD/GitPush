@echo off
setlocal enabledelayedexpansion

echo ========================================
echo GitPush Windows 一键安装向导
echo ========================================
echo.
echo 此向导将帮助您完成 GitPush 的完整安装和配置
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 没有管理员权限，某些功能可能受限
    echo.
    set /p "CONTINUE=是否继续? (y/n): "
    if /i "!CONTINUE!" neq "y" (
        echo [INFO] 安装已取消
        pause
        exit /b 1
    )
)

REM 显示安装选项
echo 请选择安装方式:
echo.
echo 1. 完整安装（推荐）
echo    - 自动安装所有依赖
echo    - 配置开发环境
echo    - 构建应用程序
echo.
echo 2. 仅安装依赖
echo    - 安装 Node.js, Python, Rust, Git
echo    - 不构建应用程序
echo.
echo 3. 仅构建应用程序
echo    - 假设依赖已安装
echo    - 直接构建应用程序
echo.
echo 4. 自定义安装
echo    - 选择性安装组件
echo.
echo 5. 查看系统要求
echo.
echo 6. 退出
echo.
set /p "INSTALL_TYPE=请输入选择 (1-6): "

if "%INSTALL_TYPE%" equ "1" goto :full_install
if "%INSTALL_TYPE%" equ "2" goto :install_deps_only
if "%INSTALL_TYPE%" equ "3" goto :build_only
if "%INSTALL_TYPE%" equ "4" goto :custom_install
if "%INSTALL_TYPE%" equ "5" goto :show_requirements
if "%INSTALL_TYPE%" equ "6" goto :exit

echo [ERROR] 无效的选择
pause
exit /b 1

:full_install
echo.
echo [INFO] 开始完整安装...
echo.

REM 调用依赖安装脚本
echo [步骤 1/4] 安装和配置 Git...
call setup-git.bat
if %errorlevel% neq 0 (
    echo [ERROR] Git 安装失败
    pause
    exit /b 1
)

echo.
echo [步骤 2/4] 安装和配置 Python...
call setup-python.bat
if %errorlevel% neq 0 (
    echo [ERROR] Python 安装失败
    pause
    exit /b 1
)

echo.
echo [步骤 3/4] 检查其他依赖...
call :check_other_deps
if %errorlevel% neq 0 (
    echo [ERROR] 依赖检查失败
    pause
    exit /b 1
)

echo.
echo [步骤 4/4] 构建应用程序...
call build-windows-enhanced.bat
if %errorlevel% neq 0 (
    echo [ERROR] 应用构建失败
    pause
    exit /b 1
)

goto :success

:install_deps_only
echo.
echo [INFO] 安装依赖项...
echo.

echo [步骤 1/2] 安装和配置 Git...
call setup-git.bat
if %errorlevel% neq 0 (
    echo [ERROR] Git 安装失败
    pause
    exit /b 1
)

echo.
echo [步骤 2/2] 安装和配置 Python...
call setup-python.bat
if %errorlevel% neq 0 (
    echo [ERROR] Python 安装失败
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 依赖安装完成！
echo 您现在可以运行 build-windows.bat 来构建应用程序
pause
exit /b 0

:build_only
echo.
echo [INFO] 构建应用程序...
echo.

call build-windows-enhanced.bat
if %errorlevel% neq 0 (
    echo [ERROR] 应用构建失败
    pause
    exit /b 1
)

goto :success

:custom_install
echo.
echo 请选择要安装的组件:
echo.
echo 1. Node.js 和 pnpm
echo 2. Rust 和 Cargo
echo 3. Python 和 pip
echo 4. Git
echo 5. 所有依赖
echo 6. 返回主菜单
echo.
set /p "COMPONENT=请输入选择 (1-6): "

if "%COMPONENT%" equ "1" call :install_nodejs
if "%COMPONENT%" equ "2" call :install_rust
if "%COMPONENT%" equ "3" call setup-python.bat
if "%COMPONENT%" equ "4" call setup-git.bat
if "%COMPONENT%" equ "5" call :install_all_deps
if "%COMPONENT%" equ "6" goto :start

echo.
echo [INFO] 自定义安装完成
pause
exit /b 0

:show_requirements
echo.
echo ========================================
echo 系统要求
echo ========================================
echo.
echo 操作系统: Windows 10/11 (64位)
echo 内存: 至少 4GB RAM
echo 存储空间: 至少 500MB 可用空间
echo 网络: 稳定的互联网连接
echo.
echo 必需软件:
echo - Node.js 16.0 或更高版本
echo - Python 3.8 或更高版本
echo - Rust 1.70.0 或更高版本
echo - Git 2.30 或更高版本
echo.
echo 可选软件:
echo - Visual Studio Build Tools (用于某些本机模块)
echo - Windows SDK 10.0 或更高版本
echo.
pause
goto :start

:check_other_deps
REM 检查Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Node.js 未安装，正在安装...
    call :install_nodejs
) else (
    echo [SUCCESS] Node.js 已安装
)

REM 检查pnpm
where pnpm >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] pnpm 未安装，正在安装...
    npm install -g pnpm
) else (
    echo [SUCCESS] pnpm 已安装
)

REM 检查Rust
where cargo >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Rust 未安装，正在安装...
    call :install_rust
) else (
    echo [SUCCESS] Rust 已安装
)

exit /b 0

:install_nodejs
echo [INFO] 安装 Node.js...
start https://nodejs.org/en/download/
set /p "NODE_INSTALLED=Node.js 下载页面已打开，安装完成后请按回车继续: "
exit /b 0

:install_rust
echo [INFO] 安装 Rust...
powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile 'rustup-init.exe'"
if exist rustup-init.exe (
    rustup-init.exe -y --default-toolchain stable
    del rustup-init.exe
    refreshenv
)
exit /b 0

:install_all_deps
call :install_nodejs
call :install_rust
call setup-python.bat
call setup-git.bat
exit /b 0

:success
echo.
echo ========================================
echo [SUCCESS] 安装完成！
echo ========================================
echo.
echo 安装程序位置:
echo   - NSIS: frontend\src-tauri\target\release\bundle\nsis\
echo   - MSI:  frontend\src-tauri\target\release\bundle\msi\
echo.
echo 快捷方式:
echo   - 桌面: GitPush.lnk
echo   - 开始菜单: GitPush 文件夹
echo.
echo 下一步:
echo 1. 运行安装程序安装 GitPush
echo 2. 启动 GitPush 并完成初始配置
echo 3. 享受使用 GitPush！
echo.
echo 如需帮助，请查看 WINDOWS_INSTALL_GUIDE.md
echo.
pause
exit /b 0

:exit
echo [INFO] 安装已取消
pause
exit /b 0

:start
cls
goto :eof