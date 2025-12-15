#!/usr/bin/env python3
from pathlib import Path

# 常量配置
APP_NAME = "gitpush"
GITHUB_API_BASE_URL = "https://api.github.com"

# 路径配置
HOME_DIR = Path.home()
TOKEN_PATH = HOME_DIR / ".gitpush_token"
GIT_WORKSPACE = Path("git_workspace").resolve()
TEMP_PATH = GIT_WORKSPACE / "temp"
LOG_FILE = Path("gitpush.log").resolve()

# Git 配置
DEFAULT_GIT_USERNAME = "gitpush-uploader"
DEFAULT_GIT_EMAIL = "gitpush@example.com"
DEFAULT_GIT_COMMIT_MSG = "upload"

# GitHub API 相关配置
GITHUB_API_TIMEOUT = 10

# 上传限制（默认值，可通过环境变量覆盖）
# 默认总大小 200MB，文件数量 10,000，单文件默认同总大小
import os
MAX_UPLOAD_BYTES = int(os.environ.get("GITPUSH_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
MAX_UPLOAD_FILES = int(os.environ.get("GITPUSH_MAX_UPLOAD_FILES", "10000"))
