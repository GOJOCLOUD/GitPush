@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Python 环境配置工具
echo ========================================
echo.

REM 检查Python是否已安装
set "PYTHON_CMD="
set "PYTHON_VERSION="

REM 尝试查找python命令
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    for /f "tokens=*" %%i in ('python -V 2^>^&1') do set "PYTHON_VERSION=%%i"
    echo [SUCCESS] Python 已安装: !PYTHON_VERSION!
) else (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python3"
        for /f "tokens=*" %%i in ('python3 -V 2^>^&1') do set "PYTHON_VERSION=%%i"
        echo [SUCCESS] Python3 已安装: !PYTHON_VERSION!
    ) else (
        goto :install_python
    )
)

REM 检查Python版本是否满足要求
echo [INFO] 检查Python版本...
for /f "tokens=2" %%i in ("!PYTHON_VERSION!") do set "VERSION_NUM=%%i"
for /f "tokens=1,2 delims=." %%a in ("!VERSION_NUM!") do (
    set "MAJOR=%%a"
    set "MINOR=%%b"
)

if !MAJOR! lss 3 (
    echo [WARNING] Python版本过低，需要Python 3.8或更高版本
    goto :install_python
) else if !MAJOR! equ 3 (
    if !MINOR! lss 8 (
        echo [WARNING] Python版本过低，需要Python 3.8或更高版本
        goto :install_python
    )
)

REM 检查pip
echo [INFO] 检查pip...
!PYTHON_CMD! -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] pip 未安装，正在安装...
    !PYTHON_CMD! -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        echo [ERROR] pip 安装失败
        goto :error
    )
    echo [SUCCESS] pip 安装成功
) else (
    for /f "tokens=*" %%i in ('!PYTHON_CMD! -m pip --version') do echo [INFO] %%i
)

REM 设置项目Python环境
echo.
echo [INFO] 配置项目Python环境...
cd /d "%~dp0backend"

REM 检查是否存在requirements.txt
if exist requirements.txt (
    echo [INFO] 发现requirements.txt文件
    
    REM 询问是否创建虚拟环境
    set /p "CREATE_VENV=是否创建Python虚拟环境? (推荐) (y/n): "
    if /i "!CREATE_VENV!" equ "y" (
        echo [INFO] 创建虚拟环境...
        !PYTHON_CMD! -m venv venv
        if %errorlevel% equ 0 (
            echo [SUCCESS] 虚拟环境创建成功
            
            REM 激活虚拟环境
            call venv\Scripts\activate.bat
            
            REM 升级pip
            python -m pip install --upgrade pip
            
            REM 安装依赖
            echo [INFO] 安装项目依赖...
            pip install -r requirements.txt
            if %errorlevel% equ 0 (
                echo [SUCCESS] 依赖安装完成
            ) else (
                echo [ERROR] 依赖安装失败
                goto :error
            )
            
            REM 创建激活脚本
            echo @echo off > ..\activate-venv.bat
            echo call backend\venv\Scripts\activate.bat >> ..\activate-venv.bat
            echo echo 虚拟环境已激活 >> ..\activate-venv.bat
            
            echo [INFO] 已创建激活脚本: activate-venv.bat
        ) else (
            echo [ERROR] 虚拟环境创建失败
            goto :error
        )
    ) else (
        echo [INFO] 使用全局Python环境安装依赖...
        !PYTHON_CMD! -m pip install -r requirements.txt
        if %errorlevel% neq 0 (
            echo [ERROR] 依赖安装失败
            goto :error
        )
        echo [SUCCESS] 依赖安装完成
    )
) else (
    echo [WARNING] 未找到requirements.txt文件
)

REM 创建启动脚本
echo [INFO] 创建启动脚本...
echo @echo off > start-backend.bat
echo cd /d "%%~dp0backend" >> start-backend.bat
echo if exist venv\Scripts\activate.bat ( >> start-backend.bat
echo     call venv\Scripts\activate.bat >> start-backend.bat
echo ) >> start-backend.bat
echo python main.py >> start-backend.bat

echo [SUCCESS] 已创建启动脚本: start-backend.bat

goto :end

:install_python
echo [ERROR] Python 未安装或版本不满足要求
echo.
echo 请选择安装方式:
echo 1. 自动下载并安装Python 3.11
echo 2. 打开Python官网手动下载
echo 3. 跳过安装
echo.
set /p "INSTALL_CHOICE=请输入选择 (1/2/3): "

if "%INSTALL_CHOICE%" equ "1" (
    echo [INFO] 正在下载Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile 'python-installer.exe'"
    if exist python-installer.exe (
        echo [INFO] 正在安装Python...
        python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        del python-installer.exe
        
        REM 刷新环境变量
        call refreshenv
        
        REM 重新检查Python
        where python >nul 2>nul
        if %errorlevel% equ 0 (
            echo [SUCCESS] Python 安装成功
            for /f "tokens=*" %%i in ('python -V 2^>^&1') do echo [INFO] 版本: %%i
            goto :check_pip
        ) else (
            echo [ERROR] Python 安装失败，请手动安装
        )
    ) else (
        echo [ERROR] 无法下载Python安装程序
    )
) else if "%INSTALL_CHOICE%" equ "2" (
    echo [INFO] 正在打开Python官网...
    start https://www.python.org/downloads/windows/
) else (
    echo [INFO] 跳过Python安装
    goto :end
)

:check_pip
REM 检查pip
python -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] pip 未安装，正在安装...
    python -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        echo [ERROR] pip 安装失败
        goto :error
    )
    echo [SUCCESS] pip 安装成功
) else (
    for /f "tokens=*" %%i in ('python -m pip --version') do echo [INFO] %%i
)

goto :end

:error
echo.
echo [ERROR] 配置过程中发生错误
pause
exit /b 1

:end
echo.
echo ========================================
echo Python 环境配置完成
echo ========================================
echo.
echo 使用说明:
echo 1. 运行 start-backend.bat 启动后端服务
echo 2. 如果创建了虚拟环境，运行 activate-venv.bat 激活环境
echo.
pause