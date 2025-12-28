import asyncio
import aiohttp
import aiofiles
import re
import signal
import uuid
import filecmp
import fnmatch
import shutil
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from app.schemas.git import (
    GitPushResponse, GitStatusResponse, GitCancelResponse,
    ConflictStrategy, ValidateRepoResponse, ValidateBranchResponse,
    GetBranchesResponse, GitHubRepoInfo, GitHubBranchInfo,
    CreateBranchRequest, CreateBranchResponse
)
from app.core.exceptions import AppException, ErrorCode
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class GitTask:
    def __init__(self, task_id: str, token: str, repo: str, branch: str, filepaths: List[str],
                 conflict_strategy: ConflictStrategy, ignore_patterns: Optional[List[str]],
                 max_total_bytes: Optional[int], max_files: Optional[int],
                 max_single_file: Optional[int], force: bool):
        self.task_id = task_id
        self.token = token
        self.repo = repo
        self.branch = branch
        self.filepaths = filepaths
        self.conflict_strategy = conflict_strategy
        self.ignore_patterns = ignore_patterns or []
        self.max_total_bytes = max_total_bytes or 200 * 1024 * 1024
        self.max_files = max_files or 10000
        self.max_single_file = max_single_file or 100 * 1024 * 1024
        self.force = force
        
        self.status = "pending"
        self.pid: Optional[int] = None
        self.process: Optional[asyncio.subprocess.Process] = None
        self.progress = ""
        self.output = ""
        self.error: Optional[str] = None
        self.created_at: Optional[float] = None
        
        self.copied_files = 0
        self.skipped_files = 0
        self.renamed_files = 0
        self.skipped_identical = 0
        self.total_size_bytes = 0
        self.total_files_count = 0


class GitService:
    process_registry: Dict[str, GitTask] = {}
    
    DEFAULT_IGNORE_PATTERNS = [
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
    
    @staticmethod
    async def _run_git_command(args: List[str], cwd: str, capture_output: bool = True) -> Tuple[int, bytes, bytes]:
        """
        在线程中执行同步 Git 命令（兼容 Windows）
        返回: (returncode, stdout, stderr)
        """
        def run_sync():
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=capture_output,
                text=False,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        
        return await asyncio.to_thread(run_sync)
    
    @staticmethod
    async def _run_git_process_async(args: List[str], cwd: str) -> subprocess.Popen:
        """
        在线程中启动 Git 进程（兼容 Windows），返回 Popen 对象
        """
        def start_process():
            return subprocess.Popen(
                args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=False
            )
        
        return await asyncio.to_thread(start_process)
    
    @staticmethod
    def mask_token(text: str, token: Optional[str] = None) -> str:
        if not token:
            return text
        masked = re.sub(re.escape(token), "***TOKEN***", text, flags=re.IGNORECASE)
        return masked
    
    @staticmethod
    async def validate_token(token: str) -> dict:
        """验证 GitHub Token 是否有效"""
        url = "https://api.github.com/user"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Token 验证成功: {data.get('login', 'unknown')}")
                        return {
                            "success": True,
                            "message": "Token validation successful",
                            "user": data.get("login")
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Token 验证失败，HTTP 状态码: {response.status}, 错误: {error_text}")
                        return {
                            "success": False,
                            "message": f"GitHub validation failed: {response.status} {response.reason}",
                            "statusCode": response.status
                        }
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            return {
                "success": False,
                "message": f"Network error: {str(e)}"
            }
    
    @staticmethod
    async def get_repos(token: str) -> dict:
        """获取用户的仓库列表"""
        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        repos = await response.json()
                        formatted_repos = [
                            {
                                "full_name": repo.get("full_name"),
                                "description": repo.get("description"),
                                "name": repo.get("name")
                            }
                            for repo in repos
                        ]
                        logger.info(f"获取仓库列表成功: {len(formatted_repos)} 个仓库")
                        return {
                            "success": True,
                            "repos": formatted_repos
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"获取仓库列表失败，HTTP 状态码: {response.status}, 错误: {error_text}")
                        return {
                            "success": False,
                            "message": f"Failed to get repository list: {response.status} {response.reason}",
                            "statusCode": response.status
                        }
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            return {
                "success": False,
                "message": f"Network error: {str(e)}"
            }
    
    @staticmethod
    async def validate_repo(token: str, repo: str) -> ValidateRepoResponse:
        """验证仓库是否存在且用户有访问权限"""
        url = f"https://api.github.com/repos/{repo}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"仓库验证成功: {repo}")
                        return ValidateRepoResponse(
                            valid=True,
                            repo_info=GitHubRepoInfo(
                                name=data.get("name", ""),
                                full_name=data.get("full_name", ""),
                                default_branch=data.get("default_branch", "")
                            )
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"仓库验证失败，HTTP 状态码: {response.status}, 错误: {error_text}")
                        return ValidateRepoResponse(
                            valid=False,
                            repo_info=None
                        )
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            return ValidateRepoResponse(
                valid=False,
                repo_info=None
            )
    
    @staticmethod
    async def validate_branch(token: str, repo: str, branch: str) -> ValidateBranchResponse:
        """验证分支是否存在"""
        url = f"https://api.github.com/repos/{repo}/branches/{branch}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"分支验证成功: {branch}")
                        return ValidateBranchResponse(
                            valid=True,
                            branch_info=GitHubBranchInfo(
                                name=data.get("name", ""),
                                sha=data.get("commit", {}).get("sha", "")
                            )
                        )
                    else:
                        logger.error(f"分支验证失败，HTTP 状态码: {response.status}")
                        return ValidateBranchResponse(
                            valid=False,
                            branch_info=None
                        )
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            return ValidateBranchResponse(
                valid=False,
                branch_info=None
            )
    
    @staticmethod
    async def get_branches(token: str, repo: str) -> GetBranchesResponse:
        """获取仓库的所有分支列表"""
        url = f"https://api.github.com/repos/{repo}/branches"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        branches = [branch["name"] for branch in data]
                        logger.info(f"成功获取 {len(branches)} 个分支")
                        
                        default_branch = None
                        if branches:
                            default_branch = await GitService._get_default_branch(token, repo)
                        
                        return GetBranchesResponse(
                            branches=branches,
                            default_branch=default_branch
                        )
                    else:
                        logger.error(f"获取分支列表失败，HTTP 状态码: {response.status}")
                        raise AppException(
                            code=ErrorCode.INTERNAL_ERROR,
                            message=f"获取分支列表失败，HTTP 状态码: {response.status}",
                            http_status=response.status
                        )
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            raise AppException(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"网络请求失败: {str(e)}",
                http_status=500
            )
    
    @staticmethod
    async def _get_default_branch(token: str, repo: str) -> Optional[str]:
        """获取仓库的默认分支"""
        url = f"https://api.github.com/repos/{repo}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("default_branch")
        except aiohttp.ClientError:
            pass
        
        return None
    
    @staticmethod
    async def _get_branch_sha(token: str, repo: str, branch_name: str) -> Optional[str]:
        """获取指定分支的 SHA 值"""
        url = f"https://api.github.com/repos/{repo}/git/refs/heads/{branch_name}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("object", {}).get("sha")
        except aiohttp.ClientError:
            pass
        
        return None
    
    @staticmethod
    async def create_branch(token: str, repo: str, new_branch: str) -> CreateBranchResponse:
        """创建新分支"""
        logger.info(f"开始创建分支: repo={repo}, branch={new_branch}")
        
        # 首先获取默认分支
        try:
            default_branch = await GitService._get_default_branch(token, repo)
            if not default_branch:
                logger.error(f"无法获取默认分支: repo={repo}")
                return CreateBranchResponse(
                    success=False,
                    message="无法获取默认分支",
                    branch_name=None
                )
            logger.info(f"获取默认分支成功: {default_branch}")
        except Exception as e:
            logger.error(f"获取默认分支时发生异常: {str(e)}", exc_info=True)
            return CreateBranchResponse(
                success=False,
                message=f"获取默认分支时发生异常: {str(e)}",
                branch_name=None
            )
        
        # 获取默认分支的 SHA 值
        try:
            default_sha = await GitService._get_branch_sha(token, repo, default_branch)
            if not default_sha:
                logger.error(f"无法获取默认分支 SHA: repo={repo}, branch={default_branch}")
                return CreateBranchResponse(
                    success=False,
                    message="无法获取默认分支 SHA",
                    branch_name=None
                )
            logger.info(f"获取默认分支 SHA 成功: {default_sha}")
        except Exception as e:
            logger.error(f"获取默认分支 SHA 时发生异常: {str(e)}", exc_info=True)
            return CreateBranchResponse(
                success=False,
                message=f"获取默认分支 SHA 时发生异常: {str(e)}",
                branch_name=None
            )
        
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
        
        logger.info(f"准备创建分支: url={url}, ref=refs/heads/{new_branch}, sha={default_sha}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    logger.info(f"GitHub API 响应: status={response.status}, body={response_text}")
                    
                    if response.status == 201:
                        logger.info(f"分支 {new_branch} 创建成功")
                        return CreateBranchResponse(
                            success=True,
                            message=f"分支 {new_branch} 创建成功",
                            branch_name=new_branch
                        )
                    else:
                        logger.error(f"创建分支失败，HTTP 状态码: {response.status}, 错误: {response_text}")
                        return CreateBranchResponse(
                            success=False,
                            message=f"创建分支失败: {response_text}",
                            branch_name=None
                        )
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}", exc_info=True)
            return CreateBranchResponse(
                success=False,
                message=f"网络请求失败: {str(e)}",
                branch_name=None
            )
        except Exception as e:
            logger.error(f"创建分支时发生未知异常: {str(e)}", exc_info=True)
            return CreateBranchResponse(
                success=False,
                message=f"创建分支时发生未知异常: {str(e)}",
                branch_name=None
            )
    
    @staticmethod
    def load_gitignore_patterns(root: Path) -> List[str]:
        """加载 .gitignore 文件中的模式"""
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
                    logger.warning(f"读取 .gitignore 失败 {gi}: {e}")
        return patterns
    
    @staticmethod
    def should_ignore(rel_path: Path, ignore_list: List[str]) -> bool:
        """检查文件是否应该被忽略"""
        rel = rel_path.as_posix()
        parts = rel_path.parts
        for pat in ignore_list:
            clean_pat = pat.rstrip("/")
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel_path.name, pat):
                return True
            if rel == clean_pat or rel.startswith(clean_pat + "/"):
                return True
            if clean_pat in parts:
                return True
        return False
    
    @staticmethod
    def get_unique_filename(dest_dir: Path, filename: str) -> str:
        """生成唯一的文件名"""
        base, ext = os.path.splitext(filename)
        counter = 1
        unique_name = filename
        while (dest_dir / unique_name).exists():
            unique_name = f"{base} ({counter}){ext}"
            counter += 1
        return unique_name
    
    @staticmethod
    def are_files_identical(file1: Path, file2: Path) -> bool:
        """检查两个文件内容是否相同"""
        return filecmp.cmp(str(file1), str(file2), shallow=False)
    
    @staticmethod
    async def process_file_async(
        src_file: Path,
        rel_path: Path,
        size: int,
        base_dest: Path,
        conflict_strategy: ConflictStrategy,
        effective_ignores: List[str],
        max_single_file: int
    ) -> Tuple[str, int, int, int, int, int]:
        """异步处理单个文件"""
        if GitService.should_ignore(rel_path, effective_ignores):
            return "skipped", 0, 0, 0, 0, 0
        
        if size > max_single_file:
            return "error", 0, 0, 0, 0, 0
        
        dest_path = base_dest / rel_path
        
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            copied = 0
            skipped = 0
            renamed = 0
            skipped_identical = 0
            total_size = 0
            
            if dest_path.exists():
                if conflict_strategy == ConflictStrategy.OVERWRITE:
                    if GitService.are_files_identical(src_file, dest_path):
                        skipped_identical = 1
                    else:
                        shutil.copy2(src_file, dest_path)
                        copied = 1
                        total_size = size
                elif conflict_strategy == ConflictStrategy.SKIP:
                    skipped = 1
                elif conflict_strategy == ConflictStrategy.RENAME:
                    unique_name = GitService.get_unique_filename(dest_path.parent, dest_path.name)
                    unique_dest = dest_path.parent / unique_name
                    shutil.copy2(src_file, unique_dest)
                    renamed = 1
                    copied = 1
                    total_size = size
            else:
                shutil.copy2(src_file, dest_path)
                copied = 1
                total_size = size
            
            return "success", copied, skipped, renamed, skipped_identical, total_size
        except Exception as e:
            logger.error(f"处理文件失败 {src_file}: {e}")
            return "error", 0, 0, 0, 0, 0
    
    @staticmethod
    async def process_files_parallel(
        task: GitTask,
        workdir: Path,
        all_files_to_process: List[Tuple[Path, Path, int, Path, ConflictStrategy, List[str]]]
    ):
        """并行处理文件"""
        max_workers = min(4, len(all_files_to_process))
        
        if max_workers > 1 and len(all_files_to_process) > 1:
            logger.info(f"并行处理 {len(all_files_to_process)} 个文件，使用 {max_workers} 个工作线程")
            
            semaphore = asyncio.Semaphore(max_workers)
            
            async def process_with_semaphore(args):
                async with semaphore:
                    return await GitService.process_file_async(*args, task.max_single_file)
            
            tasks = [process_with_semaphore(args) for args in all_files_to_process]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"文件处理异常: {result}")
                    continue
                
                status, copied, skipped, renamed, skipped_identical, total_size = result
                
                if status == "success":
                    task.copied_files += copied
                    task.skipped_files += skipped
                    task.renamed_files += renamed
                    task.skipped_identical += skipped_identical
                    task.total_size_bytes += total_size
                    logger.info(f"文件处理完成 - 复制: {copied}, 跳过: {skipped}, 重命名: {renamed}, 相同: {skipped_identical}, 大小: {total_size} 字节")
                elif status == "skipped":
                    task.skipped_files += 1
                elif status == "error":
                    logger.error(f"文件处理失败")
        else:
            logger.info(f"同步处理 {len(all_files_to_process)} 个文件")
            for args in all_files_to_process:
                src_file, rel_path, size, base_dest, conflict_strategy, effective_ignores = args
                logger.info(f"处理文件: {src_file} -> {base_dest / rel_path}")
                
                if GitService.should_ignore(rel_path, effective_ignores):
                    logger.info(f"文件被忽略: {rel_path}")
                    task.skipped_files += 1
                    continue
                
                task.total_files_count += 1
                
                if task.total_files_count > task.max_files:
                    raise AppException(
                        code=ErrorCode.BAD_REQUEST,
                        message=f"文件数量超过限制 ({task.total_files_count} > {task.max_files})",
                        http_status=400
                    )
                
                if size > task.max_single_file:
                    size_mb = size / 1024 / 1024
                    limit_mb = task.max_single_file / 1024 / 1024
                    raise AppException(
                        code=ErrorCode.BAD_REQUEST,
                        message=f"文件 {rel_path} 超过 GitHub 单文件限制 ({size_mb:.2f}MB > {limit_mb:.2f}MB)",
                        http_status=400
                    )
                
                dest_path = base_dest / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"目标路径: {dest_path}, 存在: {dest_path.exists()}")
                
                if dest_path.exists():
                    logger.info(f"目标文件已存在，冲突策略: {conflict_strategy}")
                    if conflict_strategy == ConflictStrategy.OVERWRITE:
                        if GitService.are_files_identical(src_file, dest_path):
                            logger.info(f"文件内容相同，跳过: {rel_path}")
                            task.skipped_identical += 1
                            continue
                        logger.info(f"覆盖文件: {rel_path}")
                        shutil.copy2(src_file, dest_path)
                        task.copied_files += 1
                        task.total_size_bytes += size
                    elif conflict_strategy == ConflictStrategy.SKIP:
                        logger.info(f"跳过已存在文件: {rel_path}")
                        task.skipped_files += 1
                        continue
                    elif conflict_strategy == ConflictStrategy.RENAME:
                        unique_name = GitService.get_unique_filename(dest_path.parent, dest_path.name)
                        unique_dest = dest_path.parent / unique_name
                        logger.info(f"重命名文件: {rel_path} -> {unique_name}")
                        shutil.copy2(src_file, unique_dest)
                        task.renamed_files += 1
                        task.copied_files += 1
                        task.total_size_bytes += size
                else:
                    logger.info(f"复制新文件: {rel_path}")
                    shutil.copy2(src_file, dest_path)
                    task.copied_files += 1
                    task.total_size_bytes += size
                
                logger.info(f"文件处理完成: 复制={task.copied_files}, 跳过={task.skipped_files}, 重命名={task.renamed_files}, 相同={task.skipped_identical}")
                
                if task.total_size_bytes > task.max_total_bytes:
                    raise AppException(
                        code=ErrorCode.BAD_REQUEST,
                        message=f"总大小超过限制 ({task.total_size_bytes} > {task.max_total_bytes})",
                        http_status=400
                    )
        
        task.total_files_count = task.copied_files + task.skipped_files + task.renamed_files + task.skipped_identical
    
    @staticmethod
    async def push(request) -> GitPushResponse:
        """执行 Git 推送"""
        task_id = str(uuid.uuid4())
        
        task = GitTask(
            task_id=task_id,
            token=request.token,
            repo=request.repo,
            branch=request.branch,
            filepaths=request.filepaths,
            conflict_strategy=request.conflict_strategy,
            ignore_patterns=request.ignore_patterns,
            max_total_bytes=request.max_total_bytes,
            max_files=request.max_files,
            max_single_file=request.max_single_file,
            force=request.force,
        )
        
        GitService.process_registry[task_id] = task
        
        asyncio.create_task(GitService._execute_push(task))
        
        return GitPushResponse(
            task_id=task_id,
            status="pending",
            message="Git 推送任务已创建",
        )
    
    @staticmethod
    async def _execute_push(task: GitTask):
        """执行 Git 推送的内部方法"""
        try:
            task.status = "running"
            task.created_at = asyncio.get_event_loop().time()
            
            logger.info(f"开始执行 Git 推送: task_id={task.task_id}, repo={task.repo}, branch={task.branch}")
            
            base_workspace = settings.WORK_DIR / "git_workspace"
            base_workspace.mkdir(parents=True, exist_ok=True)
            
            slug_repo = task.repo.replace("/", "_")
            workdir = base_workspace / f"{slug_repo}_{task.branch or 'main'}"
            
            is_valid_repo = False
            if workdir.exists():
                try:
                    returncode, stdout, stderr = await GitService._run_git_command(
                        ["git", "rev-parse", "--is-inside-work-tree"],
                        str(workdir)
                    )
                    is_valid_repo = returncode == 0 and stdout.strip() == b"true"
                except Exception as e:
                    logger.warning(f"检查 Git 仓库失败: {e}")
            
            if workdir.exists() and is_valid_repo:
                logger.info(f"复用现有 Git 仓库（持久化缓存）...")
                try:
                    await GitService._run_git_command(
                        ["git", "clean", "-fd"],
                        str(workdir)
                    )
                except Exception as e:
                    logger.warning(f"清理 Git 仓库失败: {e}")
                    is_valid_repo = False
            
            if workdir.exists() and not is_valid_repo:
                logger.info(f"无效的 Git 仓库，重新创建工作区...")
                try:
                    shutil.rmtree(workdir)
                except Exception as e:
                    logger.warning(f"删除工作区失败: {e}")
                    workdir = base_workspace / f"{slug_repo}_{task.branch or 'main'}_{uuid.uuid4().hex[:8]}"
                    logger.info(f"使用新工作区: {workdir}")
            
            workdir.mkdir(parents=True, exist_ok=True)
            logger.info(f"使用工作区: {workdir}")
            
            if not (workdir / ".git").exists():
                logger.info(f"初始化 Git 仓库...")
                try:
                    returncode, stdout, stderr = await GitService._run_git_command(
                        ["git", "init"],
                        str(workdir)
                    )
                    logger.info(f"Git init 进程已结束，返回码: {returncode}")
                    if returncode != 0:
                        error_msg = stderr.decode('utf-8', errors='ignore')
                        logger.error(f"Git init 失败: {error_msg}")
                        raise Exception(f"Git init 失败: {error_msg}")
                    logger.info(f"Git 仓库初始化完成")
                except Exception as e:
                    logger.error(f"Git init 过程中发生异常: {e}", exc_info=True)
                    raise
            
            logger.info(f"配置 Git 用户...")
            try:
                await GitService._run_git_command(
                    ["git", "config", "user.name", "gitpush-uploader"],
                    str(workdir)
                )
                await GitService._run_git_command(
                    ["git", "config", "user.email", "gitpush@example.com"],
                    str(workdir)
                )
                logger.info(f"Git 用户配置完成")
            except Exception as e:
                logger.warning(f"配置 Git 用户失败: {e}")
            
            logger.info(f"配置远程仓库...")
            try:
                remote_url = f"https://{task.token}:x-oauth-basic@github.com/{task.repo}.git"
                await GitService._run_git_command(
                    ["git", "remote", "remove", "origin"],
                    str(workdir)
                )
                await GitService._run_git_command(
                    ["git", "remote", "add", "origin", remote_url],
                    str(workdir)
                )
                logger.info(f"远程仓库已配置: {remote_url}")
            except Exception as e:
                logger.warning(f"配置远程仓库失败: {e}")
            
            logger.info(f"准备文件列表...")
            abs_filepaths = []
            for filepath in task.filepaths:
                filepath = os.path.abspath(filepath)
                if not os.path.exists(filepath):
                    raise AppException(
                        code=ErrorCode.NOT_FOUND,
                        message=f"本地文件不存在: {filepath}",
                        http_status=404
                    )
                abs_filepaths.append(filepath)
            
            all_files_to_process = []
            for filepath in abs_filepaths:
                filepath = Path(filepath)
                dest_dir = Path(workdir)
                
                effective_ignores = list(GitService.DEFAULT_IGNORE_PATTERNS) + task.ignore_patterns
                gitignore_patterns = GitService.load_gitignore_patterns(filepath if filepath.is_dir() else filepath.parent)
                if gitignore_patterns:
                    effective_ignores.extend(gitignore_patterns)
                
                if filepath.is_file():
                    file_size = filepath.stat().st_size
                    logger.info(f"单个文件: {filepath.name}, 大小: {file_size} 字节 ({file_size / 1024 / 1024:.2f} MB)")
                    files_to_iterate = [(filepath, Path(filepath.name), file_size)]
                    base_dest = dest_dir
                else:
                    base_dest_name = filepath.name
                    if (dest_dir / base_dest_name).exists() and task.conflict_strategy == ConflictStrategy.RENAME:
                        base_dest_name = GitService.get_unique_filename(dest_dir, base_dest_name)
                    base_dest = dest_dir / base_dest_name
                    
                    files_to_iterate = []
                    for root, _, files in os.walk(filepath):
                        for name in files:
                            src_file = Path(root) / name
                            rel = src_file.relative_to(filepath)
                            try:
                                size = src_file.stat().st_size
                            except OSError:
                                continue
                            files_to_iterate.append((src_file, rel, size))
                    
                    total_dir_size = sum(size for _, _, size in files_to_iterate)
                    logger.info(f"目录: {filepath.name}, 文件数: {len(files_to_iterate)}, 总大小: {total_dir_size} 字节 ({total_dir_size / 1024 / 1024:.2f} MB)")
                    
                    if total_dir_size > 1 * 1024 * 1024 * 1024:
                        size_gb = total_dir_size / 1024 / 1024 / 1024
                        logger.warning(f"上传大小超过 1GB ({size_gb:.2f}GB)，可能会很慢且可能因 GitHub 限制而失败")
                
                for src_file, rel_path, size in files_to_iterate:
                    all_files_to_process.append((src_file, rel_path, size, base_dest, task.conflict_strategy, effective_ignores))
            
            logger.info(f"总共需要处理 {len(all_files_to_process)} 个文件")
            
            logger.info(f"开始并行处理文件...")
            await GitService.process_files_parallel(task, workdir, all_files_to_process)
            logger.info(f"文件处理完成")
            
            total_processed = task.copied_files + task.skipped_files + task.renamed_files + task.skipped_identical
            if total_processed == 0:
                logger.info("没有文件需要处理")
                task.status = "done"
                task.progress = "没有文件需要处理"
                return
            
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "add", "."],
                str(workdir)
            )
            
            logger.info(f"Git add 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
            
            if returncode != 0:
                task.status = "error"
                task.error = f"Git add 失败: {stderr.decode('utf-8', errors='ignore')}"
                logger.error(task.error)
                return
            
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "status", "--porcelain"],
                str(workdir)
            )
            status_output = stdout.decode('utf-8', errors='ignore')
            logger.info(f"Git status --porcelain 返回码: {returncode}, 输出: {status_output[:500]}")
            
            if not status_output.strip():
                logger.info("没有文件需要提交，跳过 commit 和 push")
                task.status = "done"
                task.progress = "没有文件需要提交"
                return
            
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "config", "user.name", "GitPush"],
                str(workdir)
            )
            logger.info(f"Git config user.name 返回码: {returncode}")
            
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "config", "user.email", "gitpush@example.com"],
                str(workdir)
            )
            logger.info(f"Git config user.email 返回码: {returncode}")

            logger.info(f"切换到分支: {task.branch}")
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "checkout", task.branch],
                str(workdir)
            )
            logger.info(f"Git checkout {task.branch} 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")

            if returncode != 0:
                logger.info(f"分支 {task.branch} 不存在，尝试创建新分支")
                returncode, stdout, stderr = await GitService._run_git_command(
                    ["git", "checkout", "-b", task.branch],
                    str(workdir)
                )
                logger.info(f"Git checkout -b {task.branch} 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")

                if returncode != 0:
                    task.status = "error"
                    task.error = f"Git checkout 失败: {stderr.decode('utf-8', errors='ignore')}"
                    logger.error(task.error)
                    return

            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "commit", "-m", "upload"],
                str(workdir)
            )
            
            logger.info(f"Git commit 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
            
            if returncode != 0:
                task.status = "error"
                task.error = f"Git commit 失败: {stderr.decode('utf-8', errors='ignore')}"
                logger.error(task.error)
                return

            logger.info(f"拉取远程分支最新代码...")
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "pull", "origin", task.branch, "--no-rebase", "--allow-unrelated-histories"],
                str(workdir)
            )
            logger.info(f"Git pull 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:500]}, stderr: {stderr.decode('utf-8', errors='ignore')[:500]}")
            
            if returncode != 0:
                logger.warning(f"Git pull 失败，将尝试强制推送: {stderr.decode('utf-8', errors='ignore')[:200]}")
            
            cmd = ["git", "push", "--progress"]
            if task.force or returncode != 0:
                cmd.append("--force")
            cmd.extend(["origin", task.branch])
            
            process = await GitService._run_git_process_async(cmd, str(workdir))
            
            task.process = process
            task.pid = process.pid
            
            logger.info(f"Git 进程已启动: task_id={task.task_id}, pid={process.pid}")
            
            async def read_output(stream, is_stderr=False):
                def read_line():
                    return stream.readline()
                
                while True:
                    line = await asyncio.to_thread(read_line)
                    if not line:
                        break
                    
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    masked_line = GitService.mask_token(line_str, task.token)
                    
                    if is_stderr:
                        if task.error:
                            task.error += "\n" + masked_line
                        else:
                            task.error = masked_line
                        logger.warning(f"Git stderr: task_id={task.task_id}, {masked_line}")
                    else:
                        task.output += masked_line + "\n"
                        task.progress = masked_line
                        logger.info(f"Git stdout: task_id={task.task_id}, {masked_line}")
            
            await asyncio.gather(
                read_output(process.stdout),
                read_output(process.stderr, is_stderr=True),
            )
            
            def wait_for_process():
                return process.wait()
            
            return_code = await asyncio.to_thread(wait_for_process)
            
            if return_code == 0:
                task.status = "done"
                task.progress = "推送完成"
                logger.info(f"Git 推送成功: task_id={task.task_id}")
            else:
                task.status = "error"
                error_msg = task.error if task.error else f"推送失败，退出码: {return_code}"
                task.error = error_msg
                logger.error(f"Git 推送失败: task_id={task.task_id}, exit_code={return_code}, error={error_msg}")
                
        except asyncio.CancelledError:
            task.status = "canceled"
            logger.info(f"Git 推送任务已取消: task_id={task.task_id}")
        except AppException as e:
            task.status = "error"
            task.error = str(e)
            logger.error(f"Git 推送过程中发生错误: task_id={task.task_id}, error={e}")
        except Exception as e:
            task.status = "error"
            task.error = str(e)
            logger.error(f"Git 推送过程中发生未预期错误: task_id={task.task_id}, error={e}")
    
    @staticmethod
    def get_status(task_id: str) -> GitStatusResponse:
        """获取任务状态"""
        task = GitService.process_registry.get(task_id)
        
        if not task:
            raise AppException(
                code=ErrorCode.NOT_FOUND,
                message=f"任务不存在: {task_id}",
                http_status=404,
            )
        
        return GitStatusResponse(
            task_id=task.task_id,
            status=task.status,
            pid=task.pid,
            progress=task.progress,
            output=task.output,
            error=task.error,
            copied_files=task.copied_files,
            skipped_files=task.skipped_files,
            renamed_files=task.renamed_files,
            skipped_identical=task.skipped_identical,
            total_size_bytes=task.total_size_bytes,
            total_files_count=task.total_files_count,
        )
    
    @staticmethod
    async def cancel(task_id: str) -> GitCancelResponse:
        """取消任务"""
        task = GitService.process_registry.get(task_id)
        
        if not task:
            raise AppException(
                code=ErrorCode.NOT_FOUND,
                message=f"任务不存在: {task_id}",
                http_status=404,
            )
        
        if task.status in ["done", "error", "canceled"]:
            return GitCancelResponse(
                task_id=task_id,
                success=False,
                message=f"任务已完成，无法取消: {task.status}",
            )
        
        if task.process and task.pid:
            try:
                task.process.terminate()
                
                try:
                    await asyncio.wait_for(task.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    task.process.kill()
                    await task.process.wait()
                
                task.status = "canceled"
                logger.info(f"Git 推送任务已取消: task_id={task.task_id}, pid={task.pid}")
                
                return GitCancelResponse(
                    task_id=task_id,
                    success=True,
                    message="任务已成功取消",
                )
                
            except Exception as e:
                logger.error(f"取消 Git 任务失败: task_id={task.task_id}, error={e}")
                raise AppException(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"取消任务失败: {str(e)}",
                    http_status=500,
                )
        
        return GitCancelResponse(
            task_id=task_id,
            success=False,
            message="任务未运行或进程不存在",
        )
    
    @staticmethod
    def cleanup_old_tasks(max_age_seconds: int = 3600):
        """清理旧任务"""
        import time
        
        current_time = time.time()
        to_remove = []
        
        for task_id, task in GitService.process_registry.items():
            if task.status in ["done", "error", "canceled"]:
                if task.created_at and (current_time - task.created_at) > max_age_seconds:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del GitService.process_registry[task_id]
            logger.info(f"已清理旧任务: task_id={task_id}")