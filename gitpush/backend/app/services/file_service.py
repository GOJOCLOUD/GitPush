import os
import aiofiles
from pathlib import Path
from typing import Optional
from app.schemas.file import FileScanResponse
from app.core.exceptions import AppException, ErrorCode
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FileService:
    @staticmethod
    def scan_path(path_str: str) -> FileScanResponse:
        try:
            path = Path(path_str)
            
            if not path.exists():
                return FileScanResponse(
                    path=path_str,
                    exists=False,
                    is_file=False,
                    is_dir=False,
                    size=0,
                    file_count=0,
                    dir_count=0,
                    error=f"路径不存在: {path_str}",
                )
            
            if path.is_file():
                try:
                    size = path.stat().st_size
                except PermissionError as e:
                    logger.warning(f"无法读取文件大小: {path}, 错误: {e}")
                    size = 0
                
                return FileScanResponse(
                    path=str(path.absolute()),
                    exists=True,
                    is_file=True,
                    is_dir=False,
                    size=size,
                    file_count=1,
                    dir_count=0,
                    error=None,
                )
            
            if path.is_dir():
                total_size = 0
                file_count = 0
                dir_count = 0
                error = None
                
                try:
                    for root, dirs, files in os.walk(path):
                        dir_count += len(dirs)
                        file_count += len(files)
                        
                        for file in files:
                            file_path = Path(root) / file
                            try:
                                total_size += file_path.stat().st_size
                            except (PermissionError, OSError) as e:
                                logger.warning(f"无法读取文件大小: {file_path}, 错误: {e}")
                                continue
                                
                except PermissionError as e:
                    logger.error(f"权限不足，无法扫描目录: {path}, 错误: {e}")
                    error = f"权限不足: {str(e)}"
                    raise AppException(
                        code=ErrorCode.FORBIDDEN,
                        message="权限不足，无法访问该目录",
                        http_status=403,
                        details={"path": path_str, "error": str(e)},
                    )
                except Exception as e:
                    logger.error(f"扫描目录时发生错误: {path}, 错误: {e}")
                    error = f"扫描失败: {str(e)}"
                    raise AppException(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="扫描目录时发生错误",
                        http_status=500,
                        details={"path": path_str, "error": str(e)},
                    )
                
                return FileScanResponse(
                    path=str(path.absolute()),
                    exists=True,
                    is_file=False,
                    is_dir=True,
                    size=total_size,
                    file_count=file_count,
                    dir_count=dir_count,
                    error=error,
                )
            
            return FileScanResponse(
                path=str(path.absolute()),
                exists=True,
                is_file=False,
                is_dir=False,
                size=0,
                file_count=0,
                dir_count=0,
                error="未知的文件类型",
            )
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"扫描路径时发生未预期的错误: {path_str}, 错误: {e}")
            raise AppException(
                code=ErrorCode.INTERNAL_ERROR,
                message="扫描路径时发生错误",
                http_status=500,
                details={"path": path_str, "error": str(e)},
            )

    @staticmethod
    async def save_token(token: str) -> dict:
        """保存 GitHub Token 到文件"""
        try:
            token_file = settings.DATA_DIR / ".gitpush_token"
            
            async with aiofiles.open(token_file, 'w') as f:
                await f.write(token)
            
            logger.info("Token 保存成功")
            return {
                "success": True,
                "message": "Token saved successfully"
            }
        except Exception as e:
            logger.error(f"保存 Token 失败: {e}")
            return {
                "success": False,
                "message": f"Failed to save token: {str(e)}"
            }
