#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import zipfile
import logging
from pathlib import Path

# 导入自定义模块
from token_manager import get_or_create_token
from branch_manager import choose_branch
from file_selector import choose_upload_path
from utils.github_api import choose_repo, validate_repo, validate_branch
from errors import GitPushError, GitCommandError, WorkspaceError
from logger import log
from config import (
    GIT_WORKSPACE, DEFAULT_GIT_USERNAME, DEFAULT_GIT_EMAIL, 
    DEFAULT_GIT_COMMIT_MSG
)


def check_git_installed():
    """检查系统是否安装 git"""
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        log("Git 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log("错误: 系统未安装 git", level=logging.ERROR)
        raise GitPushError("系统未安装 git")


def prepare_workspace():
    """创建固定工作目录 git_workspace，并在每次运行前清空所有内容"""
    log(f"准备工作区: {GIT_WORKSPACE}")
    
    # 清空工作目录
    if GIT_WORKSPACE.exists():
        shutil.rmtree(GIT_WORKSPACE)
    
    # 创建工作目录
    GIT_WORKSPACE.mkdir(exist_ok=True)
    
    log(f"工作区准备完成: {GIT_WORKSPACE}")
    return GIT_WORKSPACE


def copy_file_or_dir(upload_path, workspace):
    """根据路径类型处理上传路径"""
    log(f"处理上传路径: {upload_path}")
    
    if upload_path.is_file():
        # 如果是文件：复制到工作区
        shutil.copy2(upload_path, workspace)
        log(f"文件已复制到工作区: {upload_path.name}")
    elif upload_path.is_dir():
        # 如果是目录：先压缩成 zip，再解压到工作区，确保扁平结构
        zip_file = workspace / "temp.zip"
        
        # 创建 zip 文件
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(upload_path):
                for file in files:
                    file_path = Path(root) / file
                    # 计算相对路径，确保 zip 内为扁平结构
                    arcname = file_path.name
                    zf.write(file_path, arcname)
        
        # 解压到工作区
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(workspace)
        
        # 删除临时 zip 文件
        zip_file.unlink()
        log(f"目录已处理并解压到工作区: {upload_path.name}")
    elif upload_path.suffix == ".zip":
        # 如果是 zip：直接解压到工作区
        with zipfile.ZipFile(upload_path, "r") as zf:
            zf.extractall(workspace)
        log(f"ZIP 文件已解压到工作区: {upload_path.name}")
    else:
        # 否则：报错并退出
        log(f"错误: 不支持的文件类型: {upload_path}", level=logging.ERROR)
        raise GitPushError(f"不支持的文件类型: {upload_path}")
    
    return True


def run_git_command(cmd, cwd=None, ignore_errors=False):
    """运行 git 命令并返回结果"""
    log(f"执行 Git 命令: {' '.join(cmd)}", level=logging.DEBUG)
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        log(f"Git 命令执行成功: {' '.join(cmd)}", level=logging.DEBUG)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if ignore_errors:
            log(f"Git 命令执行失败但已忽略: {' '.join(cmd)}", level=logging.DEBUG)
            return True, e.stdout.strip()
        else:
            log(f"Git 命令执行失败: {' '.join(cmd)}，错误: {e.stderr.strip()}", level=logging.ERROR)
            raise GitCommandError(f"Git 命令执行失败: {' '.join(cmd)}，错误: {e.stderr.strip()}")


def switch_branch(token, repo, branch, workspace):
    """切换或创建分支"""
    log(f"切换到分支: {branch}")
    
    # 配置用户名和邮箱
    run_git_command(["git", "config", "user.name", DEFAULT_GIT_USERNAME], cwd=workspace, ignore_errors=True)
    run_git_command(["git", "config", "user.email", DEFAULT_GIT_EMAIL], cwd=workspace, ignore_errors=True)
    
    # 添加远端
    remote_url = f"https://{token}@github.com/{repo}.git"
    run_git_command(["git", "remote", "add", "origin", remote_url], cwd=workspace)
    
    # 切换分支，如果分支不存在需要创建
    success, output = run_git_command(["git", "checkout", "-b", branch], cwd=workspace, ignore_errors=True)
    if not success:
        # 分支已存在，直接切换
        run_git_command(["git", "checkout", branch], cwd=workspace)
    
    # git pull，如果远端为空仓库则忽略 pull 错误
    run_git_command(["git", "pull", "origin", branch], cwd=workspace, ignore_errors=True)
    
    log(f"已切换到分支: {branch}")
    return True


def git_commit_push(workspace, branch):
    """执行 git commit 和 push 操作"""
    log("执行 git add / commit / push...")
    log(f"正在推送到分支：{branch} ...")
    log("这一步可能需要几秒，请耐心等待...")
    
    # git add .
    log("正在添加文件...")
    run_git_command(["git", "add", "."], cwd=workspace)
    
    # git commit -m "upload"
    log("正在提交文件...")
    success, output = run_git_command(["git", "commit", "-m", DEFAULT_GIT_COMMIT_MSG], cwd=workspace, ignore_errors=True)
    if not success:
        # 检查是否有文件变化
        success, output = run_git_command(["git", "status", "--porcelain"], cwd=workspace)
        if not success or not output:
            log("警告: 没有文件变化，跳过提交")
        else:
            raise GitCommandError(f"git commit 失败: {output}")
    
    # git push -u origin 分支名
    log("正在上传中...（请稍等）")
    run_git_command(["git", "push", "-u", "origin", branch], cwd=workspace)
    
    log("推送成功！")
    return True


def orchestrate_upload(token, repo, branch, upload_path):
    """编排上传流程"""
    log(f"开始编排上传流程: repo={repo}, branch={branch}, path={upload_path}")
    
    try:
        # 1. 检查 Git 安装
        check_git_installed()
        
        # 2. 验证仓库和分支
        validate_repo(token, repo)
        try:
            validate_branch(token, repo, branch)
        except Exception:
            log(f"分支 {branch} 不存在，将在推送时创建")
        
        # 3. 检查上传路径是否存在
        if not upload_path.exists():
            log(f"错误: 上传路径不存在: {upload_path}", level=logging.ERROR)
            return {
                "success": False,
                "message": f"Upload path does not exist: {upload_path}",
                "repo": repo,
                "branch": branch,
                "url": ""
            }
        
        # 4. 准备工作区
        workspace = prepare_workspace()
        
        # 5. 复制文件或目录到工作区
        copy_file_or_dir(upload_path, workspace)
        
        # 6. 初始化 Git 仓库
        run_git_command(["git", "init"], cwd=workspace)
        
        # 7. 切换分支
        switch_branch(token, repo, branch, workspace)
        
        # 8. 提交和推送
        git_commit_push(workspace, branch)
        
        # 9. 生成访问 URL
        files_url = f"https://github.com/{repo}/tree/{branch}/"
        log(f"上传成功！GitHub 文件访问 URL: {files_url}")
        
        return {
            "success": True,
            "message": "Upload successful",
            "repo": repo,
            "branch": branch,
            "url": files_url
        }
        
    except GitPushError as e:
        log(f"上传失败: {e}", level=logging.ERROR)
        return {
            "success": False,
            "message": str(e),
            "repo": repo,
            "branch": branch,
            "url": ""
        }
    except Exception as e:
        log(f"上传过程中发生未知错误: {e}", level=logging.ERROR)
        return {
            "success": False,
            "message": f"An unexpected error occurred: {str(e)}",
            "repo": repo,
            "branch": branch,
            "url": ""
        }


def main():
    """主入口函数"""
    try:
        # 1. 检查系统是否安装 git
        check_git_installed()
        
        # 2. 获取或创建 GitHub Token
        token = get_or_create_token()
        if not token:
            log("无法获取有效的 Token", level=logging.ERROR)
            sys.exit(1)
        
        # 3. 选择仓库
        repo_name = choose_repo(token)
        if not repo_name:
            log("无法获取有效的仓库", level=logging.ERROR)
            sys.exit(1)
        
        # 4. 选择或创建分支
        branch_name = choose_branch(token, repo_name)
        if not branch_name:
            log("无法获取有效的分支", level=logging.ERROR)
            sys.exit(1)
        
        # 5. 选择上传路径
        upload_path = choose_upload_path()
        if not upload_path:
            log("无法获取有效的上传路径", level=logging.ERROR)
            sys.exit(1)
        
        # 6. 执行上传流程
        result = orchestrate_upload(token, repo_name, branch_name, upload_path)
        
        # 7. 输出结果
        if result["success"]:
            log(f"\n上传成功！")
            log(f"GitHub 文件访问 URL: {result['url']}")
        else:
            log(f"\n上传失败: {result['message']}", level=logging.ERROR)
            sys.exit(1)
            
    except Exception as e:
        log(f"错误: 发生未知错误: {e}", level=logging.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
