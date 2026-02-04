# GitPush Windows 安装指南

## 系统要求

- **操作系统**: Windows 10/11 (64位)
- **内存**: 至少 4GB RAM
- **存储空间**: 至少 500MB 可用空间
- **网络**: 稳定的互联网连接

## 自动安装（推荐）

### 方法一：使用增强版构建脚本

1. 下载项目源代码
2. 右键点击 `build-windows-enhanced.bat`，选择"以管理员身份运行"
3. 脚本会自动检测并安装所有必要的依赖项
4. 等待构建完成

### 方法二：使用分步安装脚本

1. 首先运行 `setup-git.bat` 安装和配置 Git
2. 然后运行 `setup-python.bat` 安装和配置 Python 环境
3. 最后运行 `build-windows.bat` 进行构建

## 手动安装

如果自动安装失败，可以按照以下步骤手动安装：

### 1. 安装 Node.js

1. 访问 [https://nodejs.org/](https://nodejs.org/)
2. 下载并安装 LTS 版本
3. 验证安装：打开命令提示符，输入 `node -v` 和 `npm -v`

### 2. 安装 pnpm

```cmd
npm install -g pnpm
```

### 3. 安装 Rust

1. 访问 [https://rustup.rs/](https://rustup.rs/)
2. 下载并运行 rustup-init.exe
3. 按照提示完成安装

### 4. 安装 Python

1. 访问 [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
2. 下载 Python 3.8 或更高版本
3. 安装时勾选"Add Python to PATH"

### 5. 安装 Git

1. 访问 [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. 下载并安装 Git for Windows
3. 配置用户信息：
   ```cmd
   git config --global user.name "您的姓名"
   git config --global user.email "您的邮箱"
   ```

### 6. 构建应用

1. 打开命令提示符，切换到项目目录
2. 进入 frontend 目录：
   ```cmd
   cd frontend
   ```
3. 安装依赖：
   ```cmd
   pnpm install
   ```
4. 构建前端：
   ```cmd
   pnpm build
   ```
5. 构建应用：
   ```cmd
   pnpm tauri:build
   ```

## 安装程序使用

构建完成后，可以在以下位置找到安装程序：

- **NSIS 安装包**: `frontend\src-tauri\target\release\bundle\nsis\`
- **MSI 安装包**: `frontend\src-tauri\target\release\bundle\msi\`

双击安装程序，按照提示完成安装。

## 常见问题

### Q: 构建失败提示找不到 cargo 命令

**A**: 确保 Rust 已正确安装并添加到系统 PATH。重启命令提示符或重新启动电脑。

### Q: Python 依赖安装失败

**A**: 
1. 确保使用 Python 3.8 或更高版本
2. 尝试使用虚拟环境：
   ```cmd
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Q: Git 操作失败

**A**: 
1. 确保 Git 已正确安装
2. 配置 Git 用户信息
3. 生成并配置 SSH 密钥：
   ```cmd
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```
4. 将公钥添加到 GitHub 账户

### Q: 应用启动失败

**A**: 
1. 检查防火墙设置
2. 确保端口 8000 未被占用
3. 检查 Python 后端是否正确启动

### Q: 更新失败

**A**: 
1. 确保有管理员权限
2. 检查网络连接
3. 尝试手动下载新版本并重新安装

## 卸载

1. 打开"控制面板" > "程序和功能"
2. 找到 "GitPush" 并点击"卸载"
3. 按照提示完成卸载过程

## 技术支持

如果遇到问题，请：

1. 查看日志文件：`%APPDATA%\GitPush\logs\`
2. 访问项目 GitHub 页面提交问题
3. 提供详细的错误信息和系统环境

## 高级配置

### 配置文件位置

- 应用配置: `%APPDATA%\GitPush\config.json`
- 日志文件: `%APPDATA%\GitPush\logs\`
- 临时文件: `%TEMP%\GitPush\`

### 命令行参数

- `--help`: 显示帮助信息
- `--version`: 显示版本信息
- `--config-dir`: 显示配置目录路径
- `--log-level`: 设置日志级别 (debug, info, warn, error)

### 环境变量

- `GITPUSH_LOG_LEVEL`: 设置日志级别
- `GITPUSH_CONFIG_DIR`: 自定义配置目录
- `GITPUSH_PORT`: 自定义端口号

## 开发者信息

如果您想参与开发或自行构建，请参考项目 README 文件获取更多信息。