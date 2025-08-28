# app/main.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.middleware.request_id import RequestIDMiddleware
from app.utils.response import (
    success_response,
    error_response,
    validation_error_response,
    make_request_id,
)
# import routers
from app.routers import product, auth, cart

app = FastAPI(title="E-Commerce API")

# mount API router prefix /api/v1
from fastapi import APIRouter
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(product.router)
api_router.include_router(cart.router)
app.include_router(api_router)

# root
@app.get("/")
def root():
    return {"message": "FastAPI E-COMMERCE started successfully nih 🚀"}

# add middleware
app.add_middleware(RequestIDMiddleware)

logger = logging.getLogger("uvicorn.error")

# Validation error (pydantic)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # build fields dict
    fields = {}
    for err in exc.errors():
        loc = ".".join([str(i) for i in err.get("loc", []) if i != "body"])
        fields.setdefault(loc or "body", []).append(err.get("msg"))
    metadata = {"request_id": getattr(request.state, "request_id", make_request_id())}
    return validation_error_response(errors=fields, metadata=metadata)

# HTTPException (404, 401, etc)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    metadata = {"request_id": getattr(request.state, "request_id", make_request_id())}
    return error_response(message=str(exc.detail), code=exc.status_code, details=str(exc.detail), metadata=metadata)

# Generic unhandled exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", make_request_id())
    logger.exception("Unhandled exception (request_id=%s): %s", req_id, exc)
    metadata = {"request_id": req_id}
    return error_response(message="Internal server error", code=500, details=str(exc), metadata=metadata)
