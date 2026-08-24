"""通用响应结构。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageQuery(BaseModel):
    page: int = Field(1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(20, ge=1, le=200, description="每页条数")


class PageResult(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: list[T]


class OkResult(BaseModel):
    ok: bool = True
    message: str = "操作成功"
