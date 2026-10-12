from typing import Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class ErrorResponse(BaseModel):
    code: int
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
