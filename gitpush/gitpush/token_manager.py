#!/usr/bin/env python3
import os
import webbrowser
import urllib.request
import json
import logging
from pathlib import Path
from errors import TokenError
from logger import log
from config import TOKEN_PATH


def open_token_page():
    """打开 GitHub token 生成页面"""
    token_url = "https://github.com/settings/tokens"
    log(f"正在打开 GitHub Token 生成页面: {token_url}")
    webbrowser.open(token_url)


def validate_token(token):
    """调用 GitHub API 验证 token 是否有效"""
    if not token or not isinstance(token, str):
        raise TokenError("无效的 Token 格式")
    
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                log("Token 验证成功")
                return True
            else:
                log(f"Token 验证失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise TokenError(f"Token 验证失败，HTTP 状态码: {response.status}")
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise TokenError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise TokenError(f"解析 API 响应失败: {e}")


def get_or_create_token():
    """读取或创建本地 token 文件，并校验 token 格式"""
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "r") as f:
            token = f.read().strip()
        
        try:
            if token and validate_token(token):
                log("使用已保存的有效 Token")
                return token
            else:
                log("已保存的 Token 无效", level=logging.ERROR)
        except TokenError as e:
            log(f"已保存的 Token 验证失败: {e}", level=logging.ERROR)
    
    # Token 不存在或无效，引导用户创建新 Token
    open_token_page()
    log("请在浏览器中生成 GitHub Personal Access Token")
    
    while True:
        token = input("请输入生成的 Token: ").strip()
        try:
            if token and validate_token(token):
                # 保存 Token
                with open(TOKEN_PATH, "w") as f:
                    f.write(token)
                log("Token 已保存")
                return token
            else:
                log("无效的 Token，请重新输入", level=logging.ERROR)
        except TokenError as e:
            log(f"Token 验证失败: {e}", level=logging.ERROR)
            
        retry = input("是否重新打开 Token 生成页面？(y/n): ").strip().lower()
        if retry == "y":
            open_token_page()
