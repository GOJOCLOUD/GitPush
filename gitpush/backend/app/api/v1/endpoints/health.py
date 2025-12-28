from fastapi import APIRouter, Depends
from app.schemas.base import BaseResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=BaseResponse[dict])
async def health_check():
    return BaseResponse(
        data={
            "status": "ok",
            "environment": settings.ENV,
            "version": "2.0.0",
        }
    )


@router.get("/ready", response_model=BaseResponse[dict])
async def readiness_check():
    return BaseResponse(
        data={
            "status": "ready",
            "database": "connected",
        }
    )
