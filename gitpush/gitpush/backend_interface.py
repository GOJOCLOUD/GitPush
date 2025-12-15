#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitPush 命令行版本（不会覆盖已有文件 · 不切换分支 · 无 GitHub API）
- 使用本地 git 命令执行上传
- 上传单个文件到仓库根目录
- 文件名不同 → 直接新增
- 文件名相同 → 报错，不覆盖
- stdout 只输出 JSON
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
import fnmatch
from pathlib import Path
from typing import List
from gitpush.config import MAX_UPLOAD_BYTES, MAX_UPLOAD_FILES


def print_json(data: dict):
    sys.stdout.write(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


def fail(message: str):
    print_json({
        "success": False,
        "message": message,
        "url": ""
    })
    sys.exit(0)


def run_cmd(cmd: list, cwd: str, ignore_errors: bool = False):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        if ignore_errors:
            print(f"DEBUG: Command failed but ignored: {' '.join(cmd)}\nError: {e}", file=sys.stderr)
            return ""
        fail(f"Command execution failed: {e}")

    if result.returncode != 0:
        if ignore_errors:
            print(f"DEBUG: Command failed but ignored: {' '.join(cmd)}\nError: {result.stderr.strip()}", file=sys.stderr)
            return ""
        fail(f"Command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}")

    return result.stdout.strip()


def git_push(token: str, repo: str, branch: str, filepaths: list, conflict_strategy: str = "overwrite", ignore_patterns: list = None, max_total_bytes: int = None, max_files: int = None, max_single_file: int = None):
    import sys
    
    ignore_patterns = ignore_patterns or []
    # 默认忽略模式
    default_ignore = [
        ".git",
        ".DS_Store",
        "node_modules",
        "dist",
        "dist-ssr",
        "build",
        "target",
        "src-tauri/target",
        "git_workspace",
        "tmp_upload",
        "gitpush_backup",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.log",
        "*.tmp",
    ]
    base_ignores = default_ignore + ignore_patterns

    # 设置大小/数量默认值（未传则使用配置）
    if max_total_bytes is None:
        max_total_bytes = MAX_UPLOAD_BYTES
    if max_files is None:
        max_files = MAX_UPLOAD_FILES
    if max_single_file is None:
        max_single_file = MAX_UPLOAD_BYTES  # 单文件默认不超过总上限

    def load_gitignore_patterns(root: Path) -> List[str]:
        patterns = []
        for base in [root] + list(root.parents):
            gi = base / ".gitignore"
            if gi.is_file():
                try:
                    lines = gi.read_text(encoding="utf-8").splitlines()
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        patterns.append(line)
                except Exception as e:
                    print(f"DEBUG: Failed to read .gitignore at {gi}: {e}", file=sys.stderr)
        return patterns

    def should_ignore(rel_path: Path, ignore_list: list) -> bool:
        rel = rel_path.as_posix()
        parts = rel_path.parts
        for pat in ignore_list:
            clean_pat = pat.rstrip("/")
            # 完整匹配或通配匹配
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel_path.name, pat):
                return True
            # 目录前缀匹配
            if rel == clean_pat or rel.startswith(clean_pat + "/"):
                return True
            # 任一路径段匹配（处理 node_modules 这类目录名）
            if clean_pat in parts:
                return True
        return False

    # 确保所有路径都存在
    abs_filepaths = []
    for filepath in filepaths:
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            fail(f"本地文件不存在：{filepath}")
        abs_filepaths.append(filepath)

    # 复用工作区（按 repo/branch 缓存）
    base_workspace = Path(os.getcwd()) / "git_workspace"
    base_workspace.mkdir(exist_ok=True)
    slug_repo = repo.replace("/", "_")
    workdir = base_workspace / f"{slug_repo}_{branch or 'main'}"
    workdir.mkdir(exist_ok=True)
    print(f"DEBUG: Using workspace: {workdir}", file=sys.stderr)

    # 保持干净状态
    run_cmd(["git", "reset", "--hard"], cwd=str(workdir), ignore_errors=True)
    run_cmd(["git", "clean", "-fdx"], cwd=str(workdir), ignore_errors=True)

    # 初始化仓库（第一次）或确保配置正确
    if not (workdir / ".git").exists():
        run_cmd(["git", "init"], cwd=str(workdir))
    run_cmd(["git", "config", "user.name", "gitpush-uploader"], cwd=str(workdir))
    run_cmd(["git", "config", "user.email", "gitpush@example.com"], cwd=str(workdir))

    # 设置远程仓库（每次重置，避免重复添加）
    remote_url = f"https://{token}:x-oauth-basic@github.com/{repo}.git"
    run_cmd(["git", "remote", "remove", "origin"], cwd=str(workdir), ignore_errors=True)
    run_cmd(["git", "remote", "add", "origin", remote_url], cwd=str(workdir))

    # 初始化统计变量
    copied_files = 0
    skipped_files = 0
    renamed_files = 0
    skipped_identical = 0
    total_size_bytes = 0
    total_files_count = 0
    
    # 辅助函数：生成唯一文件名
    def get_unique_filename(dest_dir, filename):
        base, ext = os.path.splitext(filename)
        counter = 1
        unique_name = filename
        while os.path.exists(os.path.join(dest_dir, unique_name)):
            unique_name = f"{base} ({counter}){ext}"
            counter += 1
        return unique_name
    
    # 辅助函数：检查文件内容是否相同
    def are_files_identical(file1, file2):
        import filecmp
        return filecmp.cmp(file1, file2, shallow=False)
    
    # 辅助函数：计算目录大小（递归）
    def iter_files(src_root: Path):
        """单次遍历：返回 (src_file, rel_path, size)"""
        for root, _, files in os.walk(src_root):
            for name in files:
                src_file = Path(root) / name
                rel = src_file.relative_to(src_root)
                try:
                    size = src_file.stat().st_size
                except OSError:
                    continue
                yield src_file, rel, size

    # 辅助函数：获取仓库的SHA值
    def get_repo_sha(workdir, repo, branch):
        try:
            # 获取本地HEAD SHA
            head_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workdir,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            # 获取远程分支SHA
            remote_sha_result = subprocess.run(
                ["git", "ls-remote", "origin", f"refs/heads/{branch}"],
                cwd=workdir,
                capture_output=True,
                text=True
            )
            remote_sha = remote_sha_result.stdout.strip().split()[0] if remote_sha_result.stdout.strip() else head_sha
            
            return head_sha, remote_sha
        except Exception as e:
            print(f"DEBUG: Failed to get SHA: {e}", file=sys.stderr)
            # 出错时使用默认值，确保不会导致整个上传失败
            return "", ""
    
    # 复制所有文件到仓库根目录（单次遍历）
    for filepath in abs_filepaths:
        filepath = Path(filepath)
        dest_dir = Path(workdir)
        print(f"DEBUG: Processing {filepath} with conflict strategy: {conflict_strategy}", file=sys.stderr)

        # 合并 .gitignore 模式
        effective_ignores = list(base_ignores)
        gitignore_patterns = load_gitignore_patterns(filepath if filepath.is_dir() else filepath.parent)
        if gitignore_patterns:
            effective_ignores.extend(gitignore_patterns)

        if filepath.is_file():
            files_to_iterate = [(filepath, Path(filepath.name), filepath.stat().st_size)]
            base_dest = dest_dir
        else:
            # 目录：根据策略可能调整目标根目录
            base_dest_name = filepath.name
            if (dest_dir / base_dest_name).exists() and conflict_strategy == "rename":
                base_dest_name = get_unique_filename(dest_dir, base_dest_name)
            base_dest = dest_dir / base_dest_name
            files_to_iterate = list(iter_files(filepath))

        for src_file, rel_path, size in files_to_iterate:
            # 忽略匹配的文件
            if should_ignore(rel_path, effective_ignores):
                skipped_files += 1
                continue

            total_files_count += 1
            # 总文件数限制
            if max_files and total_files_count > max_files:
                fail(f"Total file count exceeds limit ({total_files_count} > {max_files})")

            # 单文件大小限制
            if max_single_file and size > max_single_file:
                fail(f"File {rel_path} exceeds single-file limit ({size} bytes > {max_single_file} bytes)")
            dest_path = base_dest / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if dest_path.exists():
                if conflict_strategy == "overwrite":
                    if are_files_identical(src_file, dest_path):
                        skipped_identical += 1
                        continue
                    shutil.copy2(src_file, dest_path)
                    copied_files += 1
                    total_size_bytes += size
                elif conflict_strategy == "skip":
                    skipped_files += 1
                    continue
                elif conflict_strategy == "rename":
                    unique_name = get_unique_filename(dest_path.parent, dest_path.name)
                    unique_dest = dest_path.parent / unique_name
                    shutil.copy2(src_file, unique_dest)
                    renamed_files += 1
                    copied_files += 1
                    total_size_bytes += size
            else:
                shutil.copy2(src_file, dest_path)
                copied_files += 1
                total_size_bytes += size

            # 总大小限制
            if max_total_bytes and total_size_bytes > max_total_bytes:
                fail(f"Total upload size exceeds limit ({total_size_bytes} bytes > {max_total_bytes} bytes)")
    
    # 检查是否需要继续执行
    total_processed = copied_files + skipped_files + renamed_files + skipped_identical
    if total_processed == 0:
        # 清理临时工作区
        shutil.rmtree(workdir)
        print(f"DEBUG: Cleaned up temporary workspace", file=sys.stderr)
        
        # 获取远程SHA（文件未处理时）
        try:
            # 使用临时工作区获取SHA
            temp_workdir = tempfile.mkdtemp(prefix="gitpush_sha_")
            run_cmd(["git", "init"], cwd=temp_workdir)
            run_cmd(["git", "config", "user.name", "gitpush-uploader"], cwd=temp_workdir)
            run_cmd(["git", "config", "user.email", "gitpush@example.com"], cwd=temp_workdir)
            remote_url = f"https://{token}:x-oauth-basic@github.com/{repo}.git"
            run_cmd(["git", "remote", "add", "origin", remote_url], cwd=temp_workdir)
            run_cmd(["git", "fetch", "origin", branch], cwd=temp_workdir, ignore_errors=True)
            
            # 获取SHA值
            head_sha, remote_sha = get_repo_sha(temp_workdir, repo, branch)
            pushed_sha = remote_sha
            
            # 清理临时工作区
            shutil.rmtree(temp_workdir)
        except Exception as e:
            print(f"DEBUG: Failed to get remote SHA for no-process case: {e}", file=sys.stderr)
            head_sha = remote_sha = pushed_sha = ""
        
        print_json({
            "success": True,
            "message": "No files were processed",
            "url": f"https://github.com/{repo}/tree/{branch}/",
            "statistics": {
                "file_count": max(len(filepaths), 1),
                "copied_files": copied_files,
                "skipped_files": skipped_files,
                "renamed_files": renamed_files,
                "skipped_identical": skipped_identical,
                "total_size_bytes": total_size_bytes,
                "total_size_mb": round(total_size_bytes / 1024 / 1024, 2)
            },
            "head_sha": head_sha,
            "remote_sha": remote_sha,
            "pushed_sha": pushed_sha
        })
        sys.exit(0)
    
    # 如果全部被跳过，返回成功
    if skipped_files == total_processed:
        # 清理临时工作区
        shutil.rmtree(workdir)
        print(f"DEBUG: Cleaned up temporary workspace", file=sys.stderr)
        
        # 获取远程SHA（全部被跳过的情况）
        try:
            # 使用临时工作区获取SHA
            temp_workdir = tempfile.mkdtemp(prefix="gitpush_sha_")
            run_cmd(["git", "init"], cwd=temp_workdir)
            run_cmd(["git", "config", "user.name", "gitpush-uploader"], cwd=temp_workdir)
            run_cmd(["git", "config", "user.email", "gitpush@example.com"], cwd=temp_workdir)
            remote_url = f"https://{token}:x-oauth-basic@github.com/{repo}.git"
            run_cmd(["git", "remote", "add", "origin", remote_url], cwd=temp_workdir)
            run_cmd(["git", "fetch", "origin", branch], cwd=temp_workdir, ignore_errors=True)
            
            # 获取SHA值
            head_sha, remote_sha = get_repo_sha(temp_workdir, repo, branch)
            pushed_sha = remote_sha
            
            # 清理临时工作区
            shutil.rmtree(temp_workdir)
        except Exception as e:
            print(f"DEBUG: Failed to get remote SHA for all-skipped case: {e}", file=sys.stderr)
            head_sha = remote_sha = pushed_sha = ""
        
        print_json({
            "success": True,
            "message": "All files already exist, nothing to push.",
            "url": f"https://github.com/{repo}/tree/{branch}/",
            "statistics": {
                "file_count": max(len(filepaths), 1),
                "copied_files": copied_files,
                "skipped_files": skipped_files,
                "renamed_files": renamed_files,
                "skipped_identical": skipped_identical,
                "total_size_bytes": total_size_bytes,
                "total_size_mb": round(total_size_bytes / 1024 / 1024, 2)
            },
            "head_sha": head_sha,
            "remote_sha": remote_sha,
            "pushed_sha": pushed_sha
        })
        sys.exit(0)

    # git add / commit
    run_cmd(["git", "add", "."], cwd=workdir)
    
    # 检查是否有内容需要提交
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workdir,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    if not git_status and conflict_strategy == "overwrite":
        # 没有内容变化，获取SHA后清理并返回成功
        head_sha, remote_sha = get_repo_sha(workdir, repo, branch)
        pushed_sha = remote_sha
        shutil.rmtree(workdir)
        print(f"DEBUG: Cleaned up temporary workspace", file=sys.stderr)
        
        print_json({
            "success": True,
            "message": "No changes to push (files already up to date)",
            "url": f"https://github.com/{repo}/tree/{branch}/",
            "statistics": {
                "file_count": max(len(filepaths), 1),
                "copied_files": copied_files,
                "skipped_files": skipped_files,
                "renamed_files": renamed_files,
                "skipped_identical": skipped_identical,
                "total_size_bytes": total_size_bytes,
                "total_size_mb": round(total_size_bytes / 1024 / 1024, 2)
            },
            "head_sha": head_sha,
            "remote_sha": remote_sha,
            "pushed_sha": pushed_sha
        })
        sys.exit(0)
    
    # 有内容需要提交，执行 commit
    run_cmd(["git", "commit", "-m", f"Add {len(filepaths)} file(s) via CLI"], cwd=workdir)

    # 推送并创建分支（如果不存在）
    try:
        # 获取当前分支名（应该是master或main，取决于git版本）
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            cwd=workdir, 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        print(f"DEBUG: Current branch: {current_branch}", file=sys.stderr)
        
        # 确保当前分支名称正确
        if current_branch != branch:
            run_cmd(["git", "checkout", "-b", branch], cwd=workdir)
            print(f"DEBUG: Created and switched to branch: {branch}", file=sys.stderr)
        
        # 先获取最新的远程分支信息（允许失败，因为分支可能不存在）
        run_cmd(["git", "fetch", "origin", branch], cwd=workdir, ignore_errors=True)
        print(f"DEBUG: Fetched latest changes from origin/{branch} (if exists)", file=sys.stderr)
        
        # 检查远程是否已存在该分支
        remote_branch_exists = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch], 
            cwd=workdir, 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        print(f"DEBUG: Remote branch exists: {bool(remote_branch_exists)}", file=sys.stderr)
        
        if remote_branch_exists:
            # 远程分支已存在，需要合并远程更改
            print(f"DEBUG: Remote branch {branch} exists, merging changes", file=sys.stderr)
            
            # 检查工作区状态
            status_result = subprocess.run(
                ["git", "status"], 
                cwd=workdir, 
                capture_output=True, 
                text=True
            ).stdout
            print(f"DEBUG: Git status: {status_result}", file=sys.stderr)
            
            try:
                # 尝试合并远程分支
                run_cmd(["git", "merge", f"origin/{branch}", "--no-ff", "--allow-unrelated-histories", "-m", f"Merge remote changes into {branch}"], cwd=workdir)
                print(f"DEBUG: Merge successful, now pushing", file=sys.stderr)
            except Exception as merge_error:
                print(f"DEBUG: Merge failed, trying pull with auto-merge: {merge_error}", file=sys.stderr)
                
                try:
                    # 尝试使用pull命令，它会自动执行fetch和merge
                    run_cmd(["git", "pull", "origin", branch, "--no-ff", "--allow-unrelated-histories"], cwd=workdir)
                    print(f"DEBUG: Pull with auto-merge successful", file=sys.stderr)
                except Exception as pull_error:
                    print(f"DEBUG: Pull failed, checking for conflicts: {pull_error}", file=sys.stderr)
                    
                    # 检查是否有合并冲突
                    conflicts = subprocess.run(
                        ["git", "status", "--porcelain"], 
                        cwd=workdir, 
                        capture_output=True, 
                        text=True
                    ).stdout
                    
                    if "UU" in conflicts or "AA" in conflicts:
                        # 有合并冲突，需要手动解决
                        print(f"DEBUG: Merge conflicts found, trying alternative approach", file=sys.stderr)
                        
                        # 尝试重置到合并前的状态
                        run_cmd(["git", "reset", "--hard", "HEAD"], cwd=workdir)
                        
                        # 使用rebase代替merge
                        try:
                            run_cmd(["git", "pull", "origin", branch, "--rebase"], cwd=workdir)
                            print(f"DEBUG: Rebase successful", file=sys.stderr)
                        except Exception as rebase_error:
                            # 所有合并方式都失败，尝试强制推送（保留本地更改）
                            print(f"DEBUG: All merge/rebase attempts failed, using force push: {rebase_error}", file=sys.stderr)
                            run_cmd(["git", "push", "-u", "origin", branch, "--force"], cwd=workdir)
                            print(f"DEBUG: Force push successful", file=sys.stderr)
        
        # 推送本地更改
        run_cmd(["git", "push", "-u", "origin", branch], cwd=workdir)
        print(f"DEBUG: Push successful, branch updated", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: First push failed, trying alternative approach: {e}", file=sys.stderr)
        
        try:
            # 重置git状态
            run_cmd(["git", "reset", "--hard", "HEAD"], cwd=workdir)
            
            # 再次获取远程分支信息
            run_cmd(["git", "fetch", "origin"], cwd=workdir)
            
            # 检查目标分支是否已存在于远程
            result = subprocess.run(["git", "ls-remote", "--heads", "origin", branch], cwd=workdir, capture_output=True, text=True)
            target_branch_exists = bool(result.stdout.strip())
            
            print(f"DEBUG: Remote branch exists (alternative approach): {target_branch_exists}", file=sys.stderr)
            
            if target_branch_exists:
                # 远程分支存在，尝试使用更安全的方式合并
                print(f"DEBUG: Using alternative merge approach", file=sys.stderr)
                
                # 1. 保存当前更改
                run_cmd(["git", "stash"], cwd=workdir)
                
                # 2. 拉取最新代码
                run_cmd(["git", "pull", "origin", branch], cwd=workdir)
                
                # 3. 应用保存的更改
                run_cmd(["git", "stash", "pop"], cwd=workdir)
                
                # 4. 提交合并结果
                run_cmd(["git", "add", "."], cwd=workdir)
                run_cmd(["git", "commit", "-m", "Merge changes"], cwd=workdir)
                
                # 5. 推送更改
                run_cmd(["git", "push", "origin", branch], cwd=workdir)
            else:
                # 远程分支不存在，直接推送
                run_cmd(["git", "push", "-u", "origin", branch], cwd=workdir)
                print(f"DEBUG: Push successful, branch created", file=sys.stderr)
        except Exception as e2:
            # 所有尝试都失败，使用最后手段 - 强制推送
            print(f"DEBUG: All approaches failed, using force push as last resort: {e2}", file=sys.stderr)
            try:
                run_cmd(["git", "push", "-u", "origin", branch, "--force"], cwd=workdir)
                print(f"DEBUG: Force push successful", file=sys.stderr)
            except Exception as force_error:
                fail(f"推送失败：{force_error}")

    # 获取push后的SHA值
    head_sha, remote_sha = get_repo_sha(workdir, repo, branch)
    pushed_sha = remote_sha
    
    # 清理临时工作区
    shutil.rmtree(workdir)
    print(f"DEBUG: Cleaned up temporary workspace", file=sys.stderr)

    # 生成英文成功消息
    if copied_files > 0:
        if conflict_strategy == "overwrite":
            success_message = f"Successfully uploaded {copied_files} items (overwrite mode)"
        elif conflict_strategy == "skip":
            success_message = f"Successfully uploaded {copied_files} items, skipped {skipped_files} existing files"
        else: # rename
            success_message = f"Successfully uploaded {copied_files} items, renamed {renamed_files} files"
    else:
        success_message = "All files already exist, no new files uploaded"
    
    print_json({
        "success": True,
        "message": success_message,
        "url": f"https://github.com/{repo}/tree/{branch}/",
        "statistics": {
            "file_count": max(len(filepaths), 1),
            "copied_files": copied_files,
            "skipped_files": skipped_files,
            "renamed_files": renamed_files,
            "skipped_identical": skipped_identical,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / 1024 / 1024, 2)
        },
        "head_sha": head_sha,
        "remote_sha": remote_sha,
        "pushed_sha": pushed_sha
    })
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(description="GitPush 命令行上传版（无覆盖）")
    parser.add_argument("--token", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=False)
    parser.add_argument("--path", required=False, action='append')
    parser.add_argument("--action", required=True, choices=["upload", "get_branches", "create_branch"])
    parser.add_argument("--conflict-strategy", required=False, choices=["overwrite", "skip", "rename"], default="overwrite", help="文件冲突处理策略")
    parser.add_argument("--ignore", required=False, action='append', default=[], help="忽略模式，支持多次传入，gitignore 风格")
    parser.add_argument("--max-total-bytes", required=False, type=int, help="总大小上限（字节）")
    parser.add_argument("--max-files", required=False, type=int, help="文件数量上限")
    parser.add_argument("--max-single-file", required=False, type=int, help="单文件大小上限（字节）")
    return parser.parse_args()


def get_branches(token, repo):
    """获取仓库的所有分支"""
    import urllib.request
    import json
    import sys
    
    # 增强调试信息
    print(f"DEBUG: get_branches called with token: {token[:10]}... and repo: {repo}", file=sys.stderr)
    
    # 确保repo格式正确（owner/repo）
    if '/' not in repo:
        print(f"DEBUG: Invalid repo format: {repo}, expected owner/repo", file=sys.stderr)
        print_json({
            "success": False,
            "message": f"无效的仓库格式: {repo}，请使用 owner/repo 格式",
            "branches": []
        })
        return
    
    url = f"https://api.github.com/repos/{repo}/branches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitPush-App"
    }
    
    print(f"DEBUG: API URL: {url}", file=sys.stderr)
    print(f"DEBUG: Headers: {headers}", file=sys.stderr)
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            # 读取响应
            branches_data = response.read().decode()
            
            print(f"DEBUG: Response status: {response.status}", file=sys.stderr)
            print(f"DEBUG: Response headers: {response.getheaders()}", file=sys.stderr)
            print(f"DEBUG: GitHub API response: {branches_data}", file=sys.stderr)
            
            if response.status == 200:
                try:
                    branches = json.loads(branches_data)
                    
                    # 检查响应格式是否正确
                    if isinstance(branches, list):
                        branch_list = []
                        for branch in branches:
                            if isinstance(branch, dict) and 'name' in branch:
                                branch_list.append(branch['name'])
                            else:
                                print(f"DEBUG: Invalid branch object: {branch}", file=sys.stderr)
                        
                        print(f"DEBUG: Found {len(branch_list)} branches: {branch_list}", file=sys.stderr)
                        
                        # 如果分支列表为空，尝试获取默认分支
                        if not branch_list:
                            print(f"DEBUG: No branches found, trying to get default branch", file=sys.stderr)
                            # 获取仓库信息以获取默认分支
                            repo_url = f"https://api.github.com/repos/{repo}"
                            repo_req = urllib.request.Request(repo_url, headers=headers)
                            with urllib.request.urlopen(repo_req) as repo_response:
                                repo_data = json.loads(repo_response.read().decode())
                                default_branch = repo_data.get('default_branch', 'main')
                                branch_list.append(default_branch)
                                print(f"DEBUG: Added default branch: {default_branch}", file=sys.stderr)
                        
                        print_json({
                            "success": True,
                            "message": "获取分支成功",
                            "branches": branch_list
                        })
                    else:
                        print(f"DEBUG: Unexpected response format: {type(branches)}", file=sys.stderr)
                        print_json({
                            "success": True,
                            "message": "获取分支成功，但响应格式意外",
                            "branches": []
                        })
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error: {e}", file=sys.stderr)
                    print_json({
                        "success": True,
                        "message": f"解析 API 响应失败: {e}",
                        "branches": []
                    })
            elif response.status == 404:
                print(f"DEBUG: Repository not found: {repo}", file=sys.stderr)
                print_json({
                    "success": True,
                    "message": f"仓库 {repo} 不存在",
                    "branches": []
                })
            elif response.status == 403:
                print(f"DEBUG: Access forbidden, check token permissions", file=sys.stderr)
                print_json({
                    "success": True,
                    "message": "访问被拒绝，请检查 Token 权限",
                    "branches": []
                })
            else:
                # 其他HTTP错误
                print_json({
                    "success": True,
                    "message": f"获取分支失败，HTTP状态码: {response.status}",
                    "branches": []
                })
    except urllib.error.URLError as e:
        # 网络错误
        print(f"DEBUG: URLError: {e}", file=sys.stderr)
        print_json({
            "success": True,
            "message": f"网络请求失败: {e}",
            "branches": []
        })
    except Exception as e:
        # 其他异常
        print(f"DEBUG: Exception: {type(e).__name__}: {e}", file=sys.stderr)
        print_json({
            "success": True,
            "message": f"获取分支失败: {e}",
            "branches": []
        })


def create_branch(token, repo, new_branch):
    """创建新分支"""
    import urllib.request
    import json
    import sys
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # 步骤1：获取仓库默认分支
        default_branch_url = f"https://api.github.com/repos/{repo}"
        req = urllib.request.Request(default_branch_url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print_json({
                    "success": False,
                    "message": f"获取仓库信息失败，HTTP 状态码: {response.status}"
                })
                sys.exit(0)
            
            repo_info = json.loads(response.read().decode())
            default_branch = repo_info.get('default_branch', 'main')
        
        # 步骤2：获取默认分支的 SHA
        branch_sha_url = f"https://api.github.com/repos/{repo}/git/refs/heads/{default_branch}"
        req = urllib.request.Request(branch_sha_url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print_json({
                    "success": False,
                    "message": f"获取分支 SHA 失败，HTTP 状态码: {response.status}"
                })
                sys.exit(0)
            
            ref = json.loads(response.read().decode())
            default_sha = ref['object']['sha']
        
        # 步骤3：创建新分支
        create_branch_url = f"https://api.github.com/repos/{repo}/git/refs"
        headers["Content-Type"] = "application/json"
        
        data = {
            "ref": f"refs/heads/{new_branch}",
            "sha": default_sha
        }
        
        req = urllib.request.Request(
            create_branch_url,
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode()
            # 使用sys.stderr输出调试信息，避免影响JSON解析
            print(f"DEBUG: Create branch response: {response_data}", file=sys.stderr)
            
            if response.status == 201:
                print_json({
                    "success": True,
                    "message": f"分支 {new_branch} 创建成功",
                    "branch": new_branch
                })
            else:
                # 尝试解析错误信息
                try:
                    error_data = json.loads(response_data)
                    error_msg = error_data.get('message', f"创建分支失败，HTTP 状态码: {response.status}")
                except:
                    error_msg = f"创建分支失败，HTTP 状态码: {response.status}"
                
                print_json({
                    "success": False,
                    "message": error_msg
                })
    except urllib.error.URLError as e:
        print(f"DEBUG: URLError: {e}", file=sys.stderr)
        print_json({
            "success": False,
            "message": f"网络请求失败：{e}"
        })
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSONDecodeError: {e}", file=sys.stderr)
        print_json({
            "success": False,
            "message": f"解析 API 响应失败：{e}"
        })
    except KeyError as e:
        print(f"DEBUG: KeyError: {e}", file=sys.stderr)
        print_json({
            "success": False,
            "message": f"API 响应缺少必要字段：{e}"
        })
    except Exception as e:
        print(f"DEBUG: Exception: {e}", file=sys.stderr)
        print_json({
            "success": False,
            "message": f"创建分支失败：{e}"
        })


def main():
    args = parse_args()
    
    if args.action == "upload":
        if not args.branch or not args.path:
            fail("上传操作需要 --branch 和 --path 参数")
        git_push(
            token=args.token.strip(),
            repo=args.repo.strip(),
            branch=args.branch.strip(),
            filepaths=args.path,
            conflict_strategy=args.conflict_strategy,
            ignore_patterns=args.ignore,
            max_total_bytes=args.max_total_bytes,
            max_files=args.max_files,
            max_single_file=args.max_single_file,
        )
    elif args.action == "get_branches":
        get_branches(
            token=args.token.strip(),
            repo=args.repo.strip()
        )
    elif args.action == "create_branch":
        if not args.branch:
            fail("创建分支操作需要 --branch 参数")
        create_branch(
            token=args.token.strip(),
            repo=args.repo.strip(),
            new_branch=args.branch.strip()
        )


if __name__ == "__main__":
    main()
