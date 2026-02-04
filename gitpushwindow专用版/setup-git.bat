@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Git 安装和配置工具
echo ========================================
echo.

REM 检查Git是否已安装
where git >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('git --version') do set "GIT_VERSION=%%i"
    echo [SUCCESS] Git 已安装: !GIT_VERSION!
    
    REM 检查Git配置
    echo [INFO] 检查Git配置...
    git config --global --get user.name >nul 2>nul
    if %errorlevel% neq 0 (
        echo [WARNING] Git用户名未配置
        set /p "GIT_NAME=请输入Git用户名: "
        git config --global user.name "!GIT_NAME!"
    ) else (
        for /f "tokens=*" %%i in ('git config --global user.name') do echo [INFO] 用户名: %%i
    )
    
    git config --global --get user.email >nul 2>nul
    if %errorlevel% neq 0 (
        echo [WARNING] Git用户邮箱未配置
        set /p "GIT_EMAIL=请输入Git邮箱: "
        git config --global user.email "!GIT_EMAIL!"
    ) else (
        for /f "tokens=*" %%i in ('git config --global user.email') do echo [INFO] 邮箱: %%i
    )
    
    REM 检查SSH密钥
    echo [INFO] 检查SSH密钥...
    if exist "%USERPROFILE%\.ssh\id_rsa.pub" (
        echo [SUCCESS] SSH密钥已存在
        echo [INFO] 公钥内容:
        type "%USERPROFILE%\.ssh\id_rsa.pub"
    ) else (
        echo [WARNING] SSH密钥不存在
        set /p "GENERATE_SSH=是否生成新的SSH密钥? (y/n): "
        if /i "!GENERATE_SSH!" equ "y" (
            echo [INFO] 生成SSH密钥...
            ssh-keygen -t rsa -b 4096 -C "gitpush@windows" -f "%USERPROFILE%\.ssh\id_rsa" -N ""
            echo [SUCCESS] SSH密钥已生成
            echo [INFO] 公钥内容:
            type "%USERPROFILE%\.ssh\id_rsa.pub"
            echo.
            echo [INFO] 请将上述公钥添加到您的GitHub账户
        )
    )
    
    goto :end
)

REM Git未安装，提供安装选项
echo [ERROR] Git 未安装
echo.
echo 请选择安装方式:
echo 1. 自动下载并安装Git for Windows
echo 2. 打开Git官网手动下载
echo 3. 跳过安装
echo.
set /p "INSTALL_CHOICE=请输入选择 (1/2/3): "

if "%INSTALL_CHOICE%" equ "1" (
    echo [INFO] 正在下载Git for Windows...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/latest/download/Git-2.43.0-64-bit.exe' -OutFile 'git-installer.exe'"
    if exist git-installer.exe (
        echo [INFO] 正在安装Git...
        git-installer.exe /VERYSILENT /NORESTART /COMPONENTS=gitlfs,assoc,assoc_sh
        del git-installer.exe
        
        REM 刷新环境变量
        call refreshenv
        
        REM 验证安装
        where git >nul 2>nul
        if %errorlevel% equ 0 (
            echo [SUCCESS] Git 安装成功
            for /f "tokens=*" %%i in ('git --version') do echo [INFO] 版本: %%i
            
            REM 设置Git配置
            set /p "GIT_NAME=请输入Git用户名: "
            git config --global user.name "!GIT_NAME!"
            
            set /p "GIT_EMAIL=请输入Git邮箱: "
            git config --global user.email "!GIT_EMAIL!"
            
            REM 生成SSH密钥
            set /p "GENERATE_SSH=是否生成SSH密钥? (y/n): "
            if /i "!GENERATE_SSH!" equ "y" (
                ssh-keygen -t rsa -b 4096 -C "gitpush@windows" -f "%USERPROFILE%\.ssh\id_rsa" -N ""
                echo [SUCCESS] SSH密钥已生成
                echo [INFO] 公钥内容:
                type "%USERPROFILE%\.ssh\id_rsa.pub"
                echo.
                echo [INFO] 请将上述公钥添加到您的GitHub账户
            )
        ) else (
            echo [ERROR] Git 安装失败，请手动安装
        )
    ) else (
        echo [ERROR] 无法下载Git安装程序
    )
) else if "%INSTALL_CHOICE%" equ "2" (
    echo [INFO] 正在打开Git官网...
    start https://git-scm.com/download/win
) else (
    echo [INFO] 跳过Git安装
)

:end
echo.
echo ========================================
echo Git 配置完成
echo ========================================
pause