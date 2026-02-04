from pathlib import Path
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator


class FileScanRequest(BaseModel):
    path: Union[str, List[str]] = Field(..., description="文件或目录路径（支持单个路径或路径列表）")
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v) -> Union[str, List[str]]:
        if isinstance(v, str):
            if not v or not v.strip():
                raise ValueError("路径不能为空")
            return v.strip()
        elif isinstance(v, list):
            if not v:
                raise ValueError("路径列表不能为空")
            return [p.strip() for p in v if p.strip()]
        else:
            raise ValueError("路径格式不正确")


class FileScanResponse(BaseModel):
    paths: List[str] = Field(description="扫描的路径列表")
    exists: bool = Field(description="路径是否存在")
    is_file: bool = Field(description="是否为文件")
    is_dir: bool = Field(description="是否为目录")
    size: int = Field(description="总大小（字节）")
    file_count: int = Field(description="文件数量")
    dir_count: int = Field(description="目录数量")
    error: Optional[str] = Field(default=None, description="错误信息")
    is_multiple: bool = Field(default=False, description="是否为多文件扫描")
