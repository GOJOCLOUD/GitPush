from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.base import ErrorResponse


class AppException(Exception):
    def __init__(
        self,
        code: int,
        message: str,
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details
        super().__init__(message)


class ErrorCode:
    SUCCESS = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    VALIDATION_ERROR = 422
    INTERNAL_ERROR = 500
    TIMEOUT_ERROR = 504
    RATE_LIMIT_ERROR = 429


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    
    error_response = ErrorResponse(
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details,
    )
    
    return JSONResponse(
        status_code=exc.http_status,
        content=error_response.model_dump(),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    
    error_response = ErrorResponse(
        code=exc.status_code,
        message=exc.detail,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    
    errors = exc.errors()
    serializable_errors = []
    for error in errors:
        serializable_error = {
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", ""))
        }
        serializable_errors.append(serializable_error)
    
    error_response = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message="请求参数验证失败",
        request_id=request_id,
        details=serializable_errors,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    
    import traceback
    error_traceback = traceback.format_exc()
    
    error_response = ErrorResponse(
        code=ErrorCode.INTERNAL_ERROR,
        message=f"服务器内部错误: {str(exc)}",
        request_id=request_id,
        details={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": error_traceback
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )
