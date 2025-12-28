from fastapi import APIRouter, BackgroundTasks
from app.schemas.base import BaseResponse
from app.schemas.git import (
    GitPushRequest, GitPushResponse, GitStatusResponse, GitCancelResponse,
    ValidateRepoResponse, ValidateBranchResponse, GetBranchesResponse,
    CreateBranchRequest, CreateBranchResponse
)
from app.services.git_service import GitService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/validate/token")
async def validate_token(request: dict):
    try:
        token = request.get("token")
        result = await GitService.validate_token(token)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"验证 Token 失败: 错误: {e}")
        raise


@router.post("/get/repos")
async def get_repos(request: dict):
    try:
        token = request.get("token")
        result = await GitService.get_repos(token)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"获取仓库列表失败: 错误: {e}")
        raise


@router.post("/push", response_model=BaseResponse[GitPushResponse])
async def push_git(request: GitPushRequest):
    try:
        result = await GitService.push(request)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"创建 Git 推送任务失败: {request.repo}, 错误: {e}")
        raise


@router.get("/status/{task_id}", response_model=BaseResponse[GitStatusResponse])
async def get_git_status(task_id: str):
    try:
        result = GitService.get_status(task_id)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"获取 Git 任务状态失败: task_id={task_id}, 错误: {e}")
        raise


@router.post("/cancel/{task_id}", response_model=BaseResponse[GitCancelResponse])
async def cancel_git(task_id: str):
    try:
        result = await GitService.cancel(task_id)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"取消 Git 任务失败: task_id={task_id}, 错误: {e}")
        raise


@router.post("/validate/repo", response_model=BaseResponse[ValidateRepoResponse])
async def validate_repo(request: dict):
    try:
        token = request.get("token")
        repo = request.get("repo")
        result = await GitService.validate_repo(token, repo)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"验证仓库失败: repo={repo}, 错误: {e}")
        raise


@router.post("/validate/branch", response_model=BaseResponse[ValidateBranchResponse])
async def validate_branch(request: dict):
    try:
        token = request.get("token")
        repo = request.get("repo")
        branch = request.get("branch")
        result = await GitService.validate_branch(token, repo, branch)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"验证分支失败: repo={repo}, branch={branch}, 错误: {e}")
        raise


@router.get("/branches", response_model=BaseResponse[GetBranchesResponse])
async def get_branches(token: str, repo: str):
    try:
        result = await GitService.get_branches(token, repo)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"获取分支列表失败: repo={repo}, 错误: {e}")
        raise


@router.post("/create/branch", response_model=BaseResponse[CreateBranchResponse])
async def create_branch(request: CreateBranchRequest):
    try:
        logger.info(f"收到创建分支请求: repo={request.repo}, branch={request.branch}")
        result = await GitService.create_branch(request.token, request.repo, request.branch)
        logger.info(f"创建分支结果: success={result.success}, message={result.message}")
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"创建分支失败: repo={request.repo}, branch={request.branch}, 错误: {str(e)}", exc_info=True)
        raise
