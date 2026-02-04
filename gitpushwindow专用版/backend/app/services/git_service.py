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
import time
import psutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Callable
from functools import wraps
from collections import deque
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


class PerformanceMetrics:
    def __init__(self):
        self.task_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_files_processed = 0
        self.total_bytes_processed = 0
        self.avg_processing_time = 0.0
        self.total_processing_time = 0.0
        self.memory_usage_mb = 0.0
        self.cpu_usage_percent = 0.0
        self.active_tasks = 0
        self.max_concurrent_tasks = 0
        self.last_updated = time.time()

    def update(self, task_status: str, files_count: int, bytes_count: int, processing_time: float):
        self.task_count += 1
        self.total_files_processed += files_count
        self.total_bytes_processed += bytes_count
        self.total_processing_time += processing_time
        self.avg_processing_time = self.total_processing_time / self.task_count if self.task_count > 0 else 0.0

        if task_status == "done":
            self.success_count += 1
        elif task_status == "error":
            self.error_count += 1

        self.last_updated = time.time()

    def update_system_metrics(self):
        try:
            process = psutil.Process()
            self.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.cpu_usage_percent = process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"获取系统指标失败: {e}")

    def get_summary(self) -> Dict[str, Any]:
        return {
            "task_count": self.task_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": f"{(self.success_count / self.task_count * 100) if self.task_count > 0 else 0:.2f}%",
            "total_files_processed": self.total_files_processed,
            "total_bytes_processed": self.total_bytes_processed,
            "avg_processing_time": f"{self.avg_processing_time:.2f}s",
            "memory_usage_mb": f"{self.memory_usage_mb:.2f}MB",
            "cpu_usage_percent": f"{self.cpu_usage_percent:.2f}%",
            "active_tasks": self.active_tasks,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "last_updated": self.last_updated
        }


class ResourceMonitor:
    def __init__(self, max_memory_mb: int = 1024, max_cpu_percent: float = 80.0):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.memory_warning_threshold = max_memory_mb * 0.8
        self.cpu_warning_threshold = max_cpu_percent * 0.8

    def check_resources(self) -> Tuple[bool, str]:
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent(interval=0.1)

            if memory_mb > self.max_memory_mb:
                return False, f"内存使用过高: {memory_mb:.2f}MB > {self.max_memory_mb}MB"

            if cpu_percent > self.max_cpu_percent:
                return False, f"CPU使用过高: {cpu_percent:.2f}% > {self.max_cpu_percent}%"

            if memory_mb > self.memory_warning_threshold:
                logger.warning(f"内存使用接近上限: {memory_mb:.2f}MB")

            if cpu_percent > self.cpu_warning_threshold:
                logger.warning(f"CPU使用接近上限: {cpu_percent:.2f}%")

            return True, "资源使用正常"
        except Exception as e:
            logger.warning(f"资源检查失败: {e}")
            return True, "资源检查失败，假设正常"


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"{func.__name__} 失败，{current_delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 重试 {max_retries} 次后仍然失败")
                except Exception as e:
                    logger.error(f"{func.__name__} 发生不可重试的错误: {e}")
                    raise

            raise last_exception if last_exception else Exception("重试失败")
        return wrapper
    return decorator


class GitTask:
    def __init__(self, task_id: str, token: str, repo: str, branch: str, filepaths: List[str],
                 conflict_strategy: ConflictStrategy, ignore_patterns: Optional[List[str]],
                 max_total_bytes: Optional[int], max_files: Optional[int],
                 max_single_file: Optional[int], force: bool, proxy: Optional[str] = None, priority: int = 0):
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
        self.proxy = proxy
        self.priority = priority

        self.status = "pending"
        self.pid: Optional[int] = None
        self.process: Optional[asyncio.subprocess.Process] = None
        self.progress = ""
        self.output = ""
        self.error: Optional[str] = None
        self.created_at: Optional[float] = None
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

        self.copied_files = 0
        self.skipped_files = 0
        self.renamed_files = 0
        self.skipped_identical = 0
        self.total_size_bytes = 0
        self.total_files_count = 0
        self.empty_dirs_count = 0

    def get_processing_time(self) -> float:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0.0


class GitService:
    process_registry: Dict[str, GitTask] = {}
    performance_metrics = PerformanceMetrics()
    resource_monitor = ResourceMonitor(max_memory_mb=1024, max_cpu_percent=80.0)
    _cleanup_task: Optional[asyncio.Task] = None
    _monitor_task: Optional[asyncio.Task] = None
    _queue_processor_task: Optional[asyncio.Task] = None
    _initialized = False
    _task_queue: asyncio.PriorityQueue = None
    _max_concurrent_tasks = 2

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

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            cls._task_queue = asyncio.PriorityQueue()
            cls._start_cleanup_task()
            cls._start_monitor_task()
            cls._start_queue_processor()
            cls._initialized = True
            logger.info("GitService 已初始化，自动清理、监控和任务队列已启动")

    @classmethod
    def shutdown(cls):
        if cls._cleanup_task and not cls._cleanup_task.done():
            cls._cleanup_task.cancel()
        if cls._monitor_task and not cls._monitor_task.done():
            cls._monitor_task.cancel()
        if cls._queue_processor_task and not cls._queue_processor_task.done():
            cls._queue_processor_task.cancel()
        logger.info("GitService 已关闭")

    @classmethod
    async def _cleanup_task_loop(cls):
        while True:
            try:
                await asyncio.sleep(300)
                cls.cleanup_old_tasks(max_age_seconds=3600)
                cls._cleanup_zombie_processes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务出错: {e}")

    @classmethod
    def _start_cleanup_task(cls):
        if cls._cleanup_task is None or cls._cleanup_task.done():
            cls._cleanup_task = asyncio.create_task(cls._cleanup_task_loop())

    @classmethod
    async def _monitor_task_loop(cls):
        while True:
            try:
                await asyncio.sleep(60)
                cls.performance_metrics.update_system_metrics()
                cls.performance_metrics.active_tasks = sum(
                    1 for task in cls.process_registry.values() if task.status == "running"
                )
                cls.performance_metrics.max_concurrent_tasks = max(
                    cls.performance_metrics.max_concurrent_tasks,
                    cls.performance_metrics.active_tasks
                )

                resource_ok, resource_msg = cls.resource_monitor.check_resources()
                if not resource_ok:
                    logger.error(resource_msg)
                    cls.cleanup_old_tasks(max_age_seconds=1800)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控任务出错: {e}")

    @classmethod
    def _start_monitor_task(cls):
        if cls._monitor_task is None or cls._monitor_task.done():
            cls._monitor_task = asyncio.create_task(cls._monitor_task_loop())

    @classmethod
    async def _queue_processor_loop(cls):
        while True:
            try:
                priority, task = await cls._task_queue.get()
                
                running_count = sum(1 for t in cls.process_registry.values() if t.status == "running")
                if running_count >= cls._max_concurrent_tasks:
                    await asyncio.sleep(1)
                    await cls._task_queue.put((priority, task))
                    cls._task_queue.task_done()
                    continue
                
                logger.info(f"从队列中取出任务: task_id={task.task_id}, priority={priority}")
                asyncio.create_task(cls._execute_push(task))
                cls._task_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"队列处理器出错: {e}")

    @classmethod
    def _start_queue_processor(cls):
        if cls._queue_processor_task is None or cls._queue_processor_task.done():
            cls._queue_processor_task = asyncio.create_task(cls._queue_processor_loop())

    @classmethod
    def _cleanup_zombie_processes(cls):
        for task_id, task in cls.process_registry.items():
            if task.process and task.pid:
                try:
                    process = psutil.Process(task.pid)
                    if process.status() == psutil.STATUS_ZOMBIE:
                        logger.warning(f"发现僵尸进程: pid={task.pid}, task_id={task_id}")
                        process.kill()
                        logger.info(f"已清理僵尸进程: pid={task.pid}")
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logger.warning(f"清理僵尸进程失败: {e}")

    @staticmethod
    def _get_timeout_for_operation(operation: str) -> int:
        timeout_map = {
            "init": 60,
            "clone": 600,
            "pull": 600,
            "push": 1200,
            "add": 300,
            "commit": 300,
            "checkout": 300,
            "clean": 300,
            "reset": 300,
            "default": 300
        }
        return timeout_map.get(operation, timeout_map["default"])

    @staticmethod
    async def _run_git_command(args: List[str], cwd: str, capture_output: bool = True, operation: str = "default") -> Tuple[int, bytes, bytes]:
        timeout = GitService._get_timeout_for_operation(operation)

        def run_sync():
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=capture_output,
                text=False,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr

        return await asyncio.to_thread(run_sync)

    @staticmethod
    async def _run_git_process_async(args: List[str], cwd: str) -> subprocess.Popen:
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
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def validate_token(token: str, proxy: Optional[str] = None) -> dict:
        url = "https://api.github.com/user"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
            raise

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def get_repos(token: str, proxy: Optional[str] = None) -> dict:
        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
            raise

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def validate_repo(token: str, repo: str, proxy: Optional[str] = None) -> ValidateRepoResponse:
        url = f"https://api.github.com/repos/{repo}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
            raise

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def validate_branch(token: str, repo: str, branch: str, proxy: Optional[str] = None) -> ValidateBranchResponse:
        url = f"https://api.github.com/repos/{repo}/branches/{branch}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
            raise

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def get_branches(token: str, repo: str, proxy: Optional[str] = None) -> GetBranchesResponse:
        url = f"https://api.github.com/repos/{repo}/branches"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        branches = [branch["name"] for branch in data]
                        logger.info(f"成功获取 {len(branches)} 个分支")

                        default_branch = None
                        if branches:
                            default_branch = await GitService._get_default_branch(token, repo, proxy)

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
            raise

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def _get_default_branch(token: str, repo: str, proxy: Optional[str] = None) -> Optional[str]:
        url = f"https://api.github.com/repos/{repo}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("default_branch")
        except aiohttp.ClientError:
            pass

        return None

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def _get_branch_sha(token: str, repo: str, branch_name: str, proxy: Optional[str] = None) -> Optional[str]:
        url = f"https://api.github.com/repos/{repo}/git/refs/heads/{branch_name}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("object", {}).get("sha")
        except aiohttp.ClientError:
            pass

        return None

    @staticmethod
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    async def create_branch(token: str, repo: str, new_branch: str, proxy: Optional[str] = None) -> CreateBranchResponse:
        logger.info(f"开始创建分支: repo={repo}, branch={new_branch}")

        try:
            default_branch = await GitService._get_default_branch(token, repo, proxy)
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

        try:
            default_sha = await GitService._get_branch_sha(token, repo, default_branch, proxy)
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
                async with session.post(url, headers=headers, json=data, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
        rel = rel_path.as_posix()
        parts = rel_path.parts
        for pat in ignore_list:
            clean_pat = pat.rstrip("/")
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel_path.name, pat):
                return True
            # 使用os.path.sep确保跨平台兼容性
            if rel == clean_pat or rel.startswith(clean_pat + os.path.sep):
                return True
            if clean_pat in parts:
                return True
        return False

    @staticmethod
    def get_unique_filename(dest_dir: Path, filename: str) -> str:
        base, ext = os.path.splitext(filename)
        counter = 1
        unique_name = filename
        while (dest_dir / unique_name).exists():
            unique_name = f"{base} ({counter}){ext}"
            counter += 1
        return unique_name

    @staticmethod
    def are_files_identical(file1: Path, file2: Path) -> bool:
        return filecmp.cmp(str(file1), str(file2), shallow=False)

    @staticmethod
    def _calculate_optimal_workers(file_count: int) -> int:
        try:
            cpu_count = os.cpu_count() or 4
            memory_percent = psutil.virtual_memory().percent

            base_workers = min(4, file_count)

            if memory_percent > 80:
                return max(1, base_workers // 2)
            elif memory_percent > 60:
                return max(2, base_workers - 1)
            else:
                return min(cpu_count, base_workers)
        except Exception as e:
            logger.warning(f"计算最优worker数量失败: {e}, 使用默认值")
            return min(4, file_count)

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
        max_workers = GitService._calculate_optimal_workers(len(all_files_to_process))

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
            proxy=getattr(request, 'proxy', None),
            priority=getattr(request, 'priority', 0)
        )

        GitService.process_registry[task_id] = task

        await GitService._task_queue.put((-task.priority, task))

        return GitPushResponse(
            task_id=task_id,
            status="pending",
            message="Git 推送任务已添加到队列",
        )

    @staticmethod
    async def _execute_push(task: GitTask):
        try:
            task.status = "running"
            task.created_at = asyncio.get_event_loop().time()
            task.started_at = time.time()

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
                        str(workdir),
                        operation="default"
                    )
                    is_valid_repo = returncode == 0 and stdout.strip() == b"true"
                except Exception as e:
                    logger.warning(f"检查 Git 仓库失败: {e}")

            if workdir.exists() and is_valid_repo:
                logger.info(f"复用现有 Git 仓库（持久化缓存）...")
                try:
                    await GitService._run_git_command(
                        ["git", "clean", "-fd"],
                        str(workdir),
                        operation="clean"
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
                        str(workdir),
                        operation="init"
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
                if task.proxy:
                    logger.info(f"配置 Git 代理: {task.proxy}")
                    await GitService._run_git_command(
                        ["git", "config", "http.proxy", task.proxy],
                        str(workdir)
                    )
                    await GitService._run_git_command(
                        ["git", "config", "https.proxy", task.proxy],
                        str(workdir)
                    )
                else:
                    # 如果没有代理，确保清除可能存在的代理设置
                    await GitService._run_git_command(
                        ["git", "config", "--unset", "http.proxy"],
                        str(workdir)
                    )
                    await GitService._run_git_command(
                        ["git", "config", "--unset", "https.proxy"],
                        str(workdir)
                    )
                
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

            logger.info(f"同步远程仓库最新状态...")
            try:
                await GitService._run_git_command(
                    ["git", "fetch", "origin"],
                    str(workdir),
                    operation="pull"
                )
                await GitService._run_git_command(
                    ["git", "reset", "--hard", f"origin/{task.branch or 'main'}"],
                    str(workdir),
                    operation="reset"
                )
                await GitService._run_git_command(
                    ["git", "clean", "-fd"],
                    str(workdir),
                    operation="clean"
                )
                logger.info(f"工作目录已同步到远程最新状态")
            except Exception as e:
                logger.warning(f"同步远程仓库时出现警告: {e}")

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

                empty_dirs = []

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
                    for root, dirs, files in os.walk(filepath):
                        for name in files:
                            src_file = Path(root) / name
                            rel = src_file.relative_to(filepath)
                            try:
                                size = src_file.stat().st_size
                            except OSError:
                                continue
                            files_to_iterate.append((src_file, rel, size))

                        for dirname in dirs:
                            dir_path = Path(root) / dirname
                            rel_dir = dir_path.relative_to(filepath)
                            try:
                                is_empty = not any(dir_path.iterdir())
                                if is_empty:
                                    empty_dirs.append(rel_dir)
                            except OSError:
                                pass

                    if not files_to_iterate and not empty_dirs:
                        logger.warning(f"目录 {filepath.name} 是空的，没有任何文件或子目录")
                        empty_dirs.append(Path("."))
                        logger.info(f"为根目录创建空文件夹标记")

                    if empty_dirs:
                        logger.info(f"发现 {len(empty_dirs)} 个空文件夹: {empty_dirs[:5]}")

                    total_dir_size = sum(size for _, _, size in files_to_iterate)
                    logger.info(f"目录: {filepath.name}, 文件数: {len(files_to_iterate)}, 总大小: {total_dir_size} 字节 ({total_dir_size / 1024 / 1024:.2f} MB)")

                    if total_dir_size > 1 * 1024 * 1024 * 1024:
                        size_gb = total_dir_size / 1024 / 1024 / 1024
                        logger.warning(f"上传大小超过 1GB ({size_gb:.2f}GB)，可能会很慢且可能因 GitHub 限制而失败")

                for src_file, rel_path, size in files_to_iterate:
                    all_files_to_process.append((src_file, rel_path, size, base_dest, task.conflict_strategy, effective_ignores))

                for empty_dir in empty_dirs:
                    gitkeep_path = base_dest / empty_dir / ".gitkeep"
                    gitkeep_path.parent.mkdir(parents=True, exist_ok=True)
                    gitkeep_path.write_text("")
                    logger.info(f"为空文件夹创建 .gitkeep: {empty_dir}")
                    all_files_to_process.append((gitkeep_path, empty_dir / ".gitkeep", 0, base_dest, task.conflict_strategy, effective_ignores))
                    task.empty_dirs_count += 1

            logger.info(f"总共需要处理 {len(all_files_to_process)} 个文件")

            logger.info(f"开始并行处理文件...")
            await GitService.process_files_parallel(task, workdir, all_files_to_process)
            logger.info(f"文件处理完成")

            total_processed = task.copied_files + task.skipped_files + task.renamed_files + task.skipped_identical
            if total_processed == 0:
                logger.info("没有文件需要处理")
                task.status = "done"
                task.progress = "没有文件需要处理"
                task.completed_at = time.time()
                return

            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "add", "."],
                str(workdir),
                operation="add"
            )

            logger.info(f"Git add 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")

            if returncode != 0:
                task.status = "error"
                task.error = f"Git add 失败: {stderr.decode('utf-8', errors='ignore')}"
                logger.error(task.error)
                task.completed_at = time.time()
                return

            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "status", "--porcelain"],
                str(workdir)
            )
            status_output = stdout.decode('utf-8', errors='ignore')
            logger.info(f"Git status --porcelain 返回码: {returncode}, 输出: {status_output[:500]}")

            if not status_output.strip():
                error_msg = "没有文件需要提交，可能文件已被忽略或内容完全相同"
                logger.error(error_msg)
                task.status = "error"
                task.error = error_msg
                task.completed_at = time.time()
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
                str(workdir),
                operation="checkout"
            )
            logger.info(f"Git checkout {task.branch} 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")

            if returncode != 0:
                logger.info(f"分支 {task.branch} 不存在，尝试创建新分支")
                returncode, stdout, stderr = await GitService._run_git_command(
                    ["git", "checkout", "-b", task.branch],
                    str(workdir),
                    operation="checkout"
                )
                logger.info(f"Git checkout -b {task.branch} 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")

                if returncode != 0:
                    task.status = "error"
                    task.error = f"Git checkout 失败: {stderr.decode('utf-8', errors='ignore')}"
                    logger.error(task.error)
                    task.completed_at = time.time()
                    return

            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "commit", "-m", "upload"],
                str(workdir),
                operation="commit"
            )

            logger.info(f"Git commit 返回码: {returncode}, stdout: {stdout.decode('utf-8', errors='ignore')[:200]}, stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")

            if returncode != 0:
                task.status = "error"
                task.error = f"Git commit 失败: {stderr.decode('utf-8', errors='ignore')}"
                logger.error(task.error)
                task.completed_at = time.time()
                return

            logger.info(f"拉取远程分支最新代码...")
            returncode, stdout, stderr = await GitService._run_git_command(
                ["git", "pull", "origin", task.branch, "--no-rebase", "--allow-unrelated-histories"],
                str(workdir),
                operation="pull"
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

            task.completed_at = time.time()

            if return_code == 0:
                task.status = "done"
                task.progress = "推送完成"
                logger.info(f"Git 推送成功: task_id={task.task_id}")
            else:
                task.status = "error"
                error_msg = task.error if task.error else f"推送失败，退出码: {return_code}"
                task.error = error_msg
                logger.error(f"Git 推送失败: task_id={task.task_id}, exit_code={return_code}, error={error_msg}")

            GitService.performance_metrics.update(
                task.status,
                task.total_files_count,
                task.total_size_bytes,
                task.get_processing_time()
            )

        except asyncio.CancelledError:
            task.status = "canceled"
            task.completed_at = time.time()
            logger.info(f"Git 推送任务已取消: task_id={task.task_id}")
        except AppException as e:
            task.status = "error"
            task.error = str(e)
            task.completed_at = time.time()
            logger.error(f"Git 推送过程中发生错误: task_id={task.task_id}, error={e}")
        except Exception as e:
            task.status = "error"
            task.error = str(e)
            task.completed_at = time.time()
            logger.error(f"Git 推送过程中发生未预期错误: task_id={task.task_id}, error={e}")

    @staticmethod
    def get_status(task_id: str) -> GitStatusResponse:
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
            empty_dirs_count=task.empty_dirs_count,
        )

    @staticmethod
    async def cancel(task_id: str) -> GitCancelResponse:
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
                task.completed_at = time.time()
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
        import time

        current_time = time.time()
        to_remove = []

        for task_id, task in GitService.process_registry.items():
            if task.status in ["done", "error", "canceled"]:
                if task.completed_at and (current_time - task.completed_at) > max_age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del GitService.process_registry[task_id]
            logger.info(f"已清理旧任务: task_id={task_id}")

    @staticmethod
    def get_performance_metrics() -> Dict[str, Any]:
        return GitService.performance_metrics.get_summary()

    @staticmethod
    def get_task_count() -> Dict[str, int]:
        counts = {
            "total": len(GitService.process_registry),
            "pending": 0,
            "running": 0,
            "done": 0,
            "error": 0,
            "canceled": 0
        }

        for task in GitService.process_registry.values():
            counts[task.status] += 1

        return counts
