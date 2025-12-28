from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ConflictStrategy(str, Enum):
    OVERWRITE = "overwrite"
    SKIP = "skip"
    RENAME = "rename"


class GitPushRequest(BaseModel):
    token: str = Field(..., description="GitHub Token")
    repo: str = Field(..., description="仓库格式: owner/repo")
    branch: str = Field(default="main", description="推送分支")
    filepaths: List[str] = Field(..., description="要上传的文件或目录路径列表")
    conflict_strategy: ConflictStrategy = Field(default=ConflictStrategy.OVERWRITE, description="文件冲突策略")
    ignore_patterns: Optional[List[str]] = Field(default=None, description="忽略模式列表")
    max_total_bytes: Optional[int] = Field(default=None, description="总大小限制（字节）")
    max_files: Optional[int] = Field(default=None, description="文件数量限制")
    max_single_file: Optional[int] = Field(default=None, description="单文件大小限制（字节）")
    force: bool = Field(default=False, description="是否强制推送")
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Token 不能为空")
        return v.strip()
    
    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("仓库不能为空")
        if "/" not in v:
            raise ValueError("仓库格式应为 owner/repo")
        return v.strip()
    
    @field_validator("filepaths")
    @classmethod
    def validate_filepaths(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("文件路径列表不能为空")
        return [p.strip() for p in v if p.strip()]


class GitPushResponse(BaseModel):
    task_id: str = Field(description="任务ID")
    status: str = Field(description="任务状态: pending, running, done, error, canceled")
    message: str = Field(description="状态消息")


class GitStatusResponse(BaseModel):
    task_id: str = Field(description="任务ID")
    status: str = Field(description="任务状态")
    pid: Optional[int] = Field(default=None, description="进程ID")
    progress: str = Field(description="进度信息")
    output: str = Field(description="输出内容")
    error: Optional[str] = Field(default=None, description="错误信息")
    copied_files: Optional[int] = Field(default=0, description="已复制的文件数")
    skipped_files: Optional[int] = Field(default=0, description="已跳过的文件数")
    renamed_files: Optional[int] = Field(default=0, description="已重命名的文件数")
    skipped_identical: Optional[int] = Field(default=0, description="已跳过的相同文件数")
    total_size_bytes: Optional[int] = Field(default=0, description="总大小（字节）")
    total_files_count: Optional[int] = Field(default=0, description="总文件数")


class GitCancelResponse(BaseModel):
    task_id: str = Field(description="任务ID")
    success: bool = Field(description="是否成功取消")
    message: str = Field(description="取消消息")


class GitHubRepoInfo(BaseModel):
    name: str = Field(description="仓库名称")
    full_name: str = Field(description="仓库全名")
    default_branch: str = Field(description="默认分支")


class GitHubBranchInfo(BaseModel):
    name: str = Field(description="分支名称")
    sha: str = Field(description="分支 SHA")


class ValidateRepoResponse(BaseModel):
    valid: bool = Field(description="仓库是否有效")
    repo_info: Optional[GitHubRepoInfo] = Field(default=None, description="仓库信息")


class ValidateBranchResponse(BaseModel):
    valid: bool = Field(description="分支是否有效")
    branch_info: Optional[GitHubBranchInfo] = Field(default=None, description="分支信息")


class GetBranchesResponse(BaseModel):
    branches: List[str] = Field(description="分支列表")
    default_branch: Optional[str] = Field(default=None, description="默认分支")


class CreateBranchRequest(BaseModel):
    token: str = Field(..., description="GitHub Token")
    repo: str = Field(..., description="仓库格式: owner/repo")
    branch: str = Field(..., description="新分支名称")
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Token 不能为空")
        return v.strip()
    
    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("仓库不能为空")
        if "/" not in v:
            raise ValueError("仓库格式应为 owner/repo")
        return v.strip()
    
    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("分支名称不能为空")
        return v.strip()


class CreateBranchResponse(BaseModel):
    success: bool = Field(description="是否创建成功")
    message: str = Field(description="创建消息")
    branch_name: Optional[str] = Field(default=None, description="分支名称")
