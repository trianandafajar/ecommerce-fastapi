# app/utils/response.py

from pydantic import BaseModel
from typing import Any, Optional, Dict
from uuid import uuid4
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_200_OK


# -----------------------
# Schema Helpers
# -----------------------

class Pagination(BaseModel):
    page: int
    per_page: int
    total: int


class Metadata(BaseModel):
    request_id: Optional[str] = None
    pagination: Optional[Pagination] = None
    extra: Optional[Dict[str, Any]] = None


class ErrorInfo(BaseModel):
    error_id: str
    details: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None


class StandardResponse(BaseModel):
    code: int
    status: str
    message: str
    data: Any = {}
    error: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None


# -----------------------
# Utils
# -----------------------

def make_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid4())


# -----------------------
# Response Generators
# -----------------------

def success_response(
    data: Any = None,
    message: str = "Success",
    code: int = HTTP_200_OK,
    metadata: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Standard success response."""
    if data is None:
        data = {}

    payload = {
        "code": code,
        "status": "success",
        "message": message,
        "data": data,
        "error": {},
        "metadata": metadata or {"request_id": make_request_id()},
    }

    return JSONResponse(status_code=code, content=jsonable_encoder(payload))


def error_response(
    message: str = "Internal server error",
    code: int = 500,
    details: Optional[str] = None,
    fields: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    error_id: Optional[str] = None,
) -> JSONResponse:
    """Standard error response."""
    err_id = error_id or make_request_id()

    payload = {
        "code": code,
        "status": "error",
        "message": message,
        "data": {},
        "error": {
            "error_id": err_id,
            "details": details or message,
            "fields": fields or {},
        },
        "metadata": metadata or {"request_id": make_request_id()},
    }

    return JSONResponse(status_code=code, content=jsonable_encoder(payload))


def validation_error_response(
    errors: Dict[str, Any],
    message: str = "Validation error",
    code: int = 422,
    metadata: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Validation error response (for pydantic/fastapi validation)."""
    err_id = make_request_id()

    payload = {
        "code": code,
        "status": "fail",
        "message": message,
        "data": {},
        "error": {
            "error_id": err_id,
            "details": "Invalid input",
            "fields": errors,
        },
        "metadata": metadata or {"request_id": make_request_id()},
    }

    return JSONResponse(status_code=code, content=jsonable_encoder(payload))
