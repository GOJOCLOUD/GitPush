from fastapi import APIRouter, HTTPException
from app.schemas.base import BaseResponse
from app.schemas.file import FileScanRequest, FileScanResponse
from app.services.file_service import FileService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scan", response_model=BaseResponse[FileScanResponse])
async def scan_path(request: FileScanRequest):
    try:
        result = FileService.scan_path(request.path)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"扫描路径失败: {request.path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save/token")
async def save_token(request: dict):
    try:
        token = request.get("token")
        result = await FileService.save_token(token)
        return BaseResponse(data=result)
    except Exception as e:
        logger.error(f"保存 Token 失败: 错误: {e}")
        raise
