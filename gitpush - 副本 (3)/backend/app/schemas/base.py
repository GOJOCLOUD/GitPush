from typing import Generic, TypeVar, Any, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="响应码，0表示成功")
    message: str = Field(default="ok", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    request_id: Optional[str] = Field(default=None, description="请求ID，用于追踪")


class ErrorResponse(BaseModel):
    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    request_id: str = Field(description="请求ID")
    details: Optional[Any] = Field(default=None, description="错误详情")
