import os
import aiofiles
from pathlib import Path
from typing import Optional, List, Union
from app.schemas.file import FileScanResponse
from app.core.exceptions import AppException, ErrorCode
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FileService:
    @staticmethod
    def scan_path(path_input: Union[str, List[str]]) -> FileScanResponse:
        try:
            logger.info(f"scan_path 调用，输入: {path_input}, 类型: {type(path_input)}")
            paths = [path_input] if isinstance(path_input, str) else path_input
            logger.info(f"处理后的路径列表: {paths}, 数量: {len(paths)}")
            
            if not paths:
                logger.warning("路径列表为空")
                return FileScanResponse(
                    paths=[],
                    exists=False,
                    is_file=False,
                    is_dir=False,
                    size=0,
                    file_count=0,
                    dir_count=0,
                    error="路径列表为空",
                    is_multiple=False,
                )
            
            if len(paths) == 1:
                logger.info(f"单个路径扫描: {paths[0]}")
                return FileService._scan_single_path(paths[0])
            else:
                logger.info(f"多路径扫描，共 {len(paths)} 个路径")
                return FileService._scan_multiple_paths(paths)
                
        except AppException:
            raise
        except Exception as e:
            logger.error(f"扫描路径时发生未预期的错误: {path_input}, 错误: {e}")
            raise AppException(
                code=ErrorCode.INTERNAL_ERROR,
                message="扫描路径时发生错误",
                http_status=500,
                details={"path": str(path_input), "error": str(e)},
            )
    
    @staticmethod
    def _scan_single_path(path_str: str) -> FileScanResponse:
        try:
            path = Path(path_str)
            
            if not path.exists():
                return FileScanResponse(
                    paths=[str(path.absolute())],
                    exists=False,
                    is_file=False,
                    is_dir=False,
                    size=0,
                    file_count=0,
                    dir_count=0,
                    error=f"路径不存在: {path_str}",
                    is_multiple=False,
                )
            
            if path.is_file():
                try:
                    size = path.stat().st_size
                except PermissionError as e:
                    logger.warning(f"无法读取文件大小: {path}, 错误: {e}")
                    size = 0
                
                return FileScanResponse(
                    paths=[str(path.absolute())],
                    exists=True,
                    is_file=True,
                    is_dir=False,
                    size=size,
                    file_count=1,
                    dir_count=0,
                    error=None,
                    is_multiple=False,
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
                    paths=[str(path.absolute())],
                    exists=True,
                    is_file=False,
                    is_dir=True,
                    size=total_size,
                    file_count=file_count,
                    dir_count=dir_count,
                    error=error,
                    is_multiple=False,
                )
            
            return FileScanResponse(
                paths=[str(path.absolute())],
                exists=True,
                is_file=False,
                is_dir=False,
                size=0,
                file_count=0,
                dir_count=0,
                error="未知的文件类型",
                is_multiple=False,
            )
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"扫描单个路径时发生错误: {path_str}, 错误: {e}")
            raise AppException(
                code=ErrorCode.INTERNAL_ERROR,
                message="扫描路径时发生错误",
                http_status=500,
                details={"path": path_str, "error": str(e)},
            )
    
    @staticmethod
    def _scan_multiple_paths(path_list: List[str]) -> FileScanResponse:
        try:
            total_size = 0
            total_file_count = 0
            total_dir_count = 0
            errors = []
            valid_paths = []
            
            for path_str in path_list:
                path = Path(path_str)
                
                if not path.exists():
                    errors.append(f"路径不存在: {path_str}")
                    continue
                
                valid_paths.append(str(path.absolute()))
                
                if path.is_file():
                    try:
                        size = path.stat().st_size
                    except PermissionError as e:
                        logger.warning(f"无法读取文件大小: {path}, 错误: {e}")
                        size = 0
                    total_size += size
                    total_file_count += 1
                elif path.is_dir():
                    try:
                        for root, dirs, files in os.walk(path):
                            total_dir_count += len(dirs)
                            total_file_count += len(files)
                            
                            for file in files:
                                file_path = Path(root) / file
                                try:
                                    total_size += file_path.stat().st_size
                                except (PermissionError, OSError) as e:
                                    logger.warning(f"无法读取文件大小: {file_path}, 错误: {e}")
                                    continue
                    except PermissionError as e:
                        logger.error(f"权限不足，无法扫描目录: {path}, 错误: {e}")
                        errors.append(f"权限不足: {path_str}")
                    except Exception as e:
                        logger.error(f"扫描目录时发生错误: {path}, 错误: {e}")
                        errors.append(f"扫描失败: {path_str}")
            
            error_msg = "; ".join(errors) if errors else None
            
            return FileScanResponse(
                paths=valid_paths,
                exists=len(valid_paths) > 0,
                is_file=False,
                is_dir=False,
                size=total_size,
                file_count=total_file_count,
                dir_count=total_dir_count,
                error=error_msg,
                is_multiple=True,
            )
            
        except Exception as e:
            logger.error(f"扫描多个路径时发生错误: {path_list}, 错误: {e}")
            raise AppException(
                code=ErrorCode.INTERNAL_ERROR,
                message="扫描多个路径时发生错误",
                http_status=500,
                details={"paths": path_list, "error": str(e)},
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
