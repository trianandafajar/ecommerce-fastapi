from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class MetaData(BaseModel):
    request_id: Optional[str] = None
    pagination: Optional[dict] = None

class SuccessResponse(GenericModel, Generic[T]):
    code: int = 200
    status: str = "success"
    message: str
    data: T
    metadata: Optional[MetaData] = None

class ErrorResponse(BaseModel):
    code: int
    status: str = "error"
    message: str
    error: Any
    error_id: Optional[str] = None
    metadata: Optional[MetaData] = None
