#!/usr/bin/env python3
import urllib.request
import json
import logging
from errors import GitHubAPIError
from logger import log


def get_repos(token):
    """获取用户的所有仓库列表"""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                log(f"获取仓库列表失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"获取仓库列表失败，HTTP 状态码: {response.status}")
            
            repos = json.loads(response.read().decode())
            # 提取仓库全名 (owner/login + name)
            repo_list = [f"{repo['owner']['login']}/{repo['name']}" for repo in repos]
            log(f"成功获取 {len(repo_list)} 个仓库")
            return repo_list
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")


def get_branches(token, repo):
    """获取仓库的所有分支列表"""
    url = f"https://api.github.com/repos/{repo}/branches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                log(f"获取分支列表失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"获取分支列表失败，HTTP 状态码: {response.status}")
            
            branches = json.loads(response.read().decode())
            # 提取分支名称
            branch_list = [branch['name'] for branch in branches]
            log(f"成功获取 {len(branch_list)} 个分支")
            return branch_list
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")


def get_default_branch(token, repo):
    """获取仓库的默认分支"""
    url = f"https://api.github.com/repos/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                log(f"获取仓库信息失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"获取仓库信息失败，HTTP 状态码: {response.status}")
            
            repo_info = json.loads(response.read().decode())
            default_branch = repo_info['default_branch']
            log(f"成功获取默认分支: {default_branch}")
            return default_branch
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")
    except KeyError:
        log("无法获取默认分支信息", level=logging.ERROR)
        raise GitHubAPIError("无法获取默认分支信息")


def get_branch_sha(token, repo, branch_name):
    """获取指定分支的 SHA 值"""
    url = f"https://api.github.com/repos/{repo}/git/refs/heads/{branch_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                log(f"获取分支 SHA 失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"获取分支 SHA 失败，HTTP 状态码: {response.status}")
            
            ref = json.loads(response.read().decode())
            sha = ref['object']['sha']
            log(f"成功获取分支 {branch_name} 的 SHA: {sha}")
            return sha
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")
    except KeyError:
        log("无法获取分支 SHA 信息", level=logging.ERROR)
        raise GitHubAPIError("无法获取分支 SHA 信息")


def create_branch(token, repo, new_branch):
    """创建新分支"""
    # 首先获取默认分支
    default_branch = get_default_branch(token, repo)
    if not default_branch:
        raise GitHubAPIError("无法获取默认分支")
    
    # 获取默认分支的 SHA 值
    default_sha = get_branch_sha(token, repo, default_branch)
    if not default_sha:
        raise GitHubAPIError("无法获取默认分支 SHA")
    
    # 创建新分支
    url = f"https://api.github.com/repos/{repo}/git/refs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    data = {
        "ref": f"refs/heads/{new_branch}",
        "sha": default_sha
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode(), 
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                log(f"分支 {new_branch} 创建成功")
                return True
            else:
                log(f"创建分支失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"创建分支失败，HTTP 状态码: {response.status}")
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")


def choose_repo(token):
    """让用户选择仓库"""
    repo_list = get_repos(token)
    if not repo_list:
        log("错误: 无法获取仓库列表", level=logging.ERROR)
        return None
    
    # 打印仓库列表
    log("\n可选仓库列表：")
    for i, repo in enumerate(repo_list, 1):
        log(f"{i}. {repo}")
    
    # 让用户选择仓库
    while True:
        try:
            choice = input("\n请输入仓库编号: ").strip()
            repo_index = int(choice) - 1
            
            if 0 <= repo_index < len(repo_list):
                repo_name = repo_list[repo_index]
                return repo_name
            else:
                log(f"错误: 编号必须在 1 到 {len(repo_list)} 之间", level=logging.ERROR)
        except ValueError:
            log("错误: 必须输入数字", level=logging.ERROR)


def validate_repo(token, repo):
    """验证仓库是否存在且用户有访问权限"""
    url = f"https://api.github.com/repos/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                log(f"仓库验证成功: {repo}")
                return True
            else:
                log(f"仓库验证失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"仓库验证失败，HTTP 状态码: {response.status}")
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")


def validate_branch(token, repo, branch):
    """验证分支是否存在"""
    url = f"https://api.github.com/repos/{repo}/branches/{branch}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                log(f"分支验证成功: {branch}")
                return True
            else:
                log(f"分支验证失败，HTTP 状态码: {response.status}", level=logging.ERROR)
                raise GitHubAPIError(f"分支验证失败，HTTP 状态码: {response.status}")
    except urllib.error.URLError as e:
        log(f"网络请求失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        log(f"解析 API 响应失败: {e}", level=logging.ERROR)
        raise GitHubAPIError(f"解析 API 响应失败: {e}")
