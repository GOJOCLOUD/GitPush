from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FileScanRequest(BaseModel):
    path: str = Field(..., description="文件或目录路径")
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("路径不能为空")
        return v.strip()


class FileScanResponse(BaseModel):
    path: str = Field(description="扫描的路径")
    exists: bool = Field(description="路径是否存在")
    is_file: bool = Field(description="是否为文件")
    is_dir: bool = Field(description="是否为目录")
    size: int = Field(description="总大小（字节）")
    file_count: int = Field(description="文件数量")
    dir_count: int = Field(description="目录数量")
    error: Optional[str] = Field(default=None, description="错误信息")
