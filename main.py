# app/main.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from sqlalchemy import text

load_dotenv()

from app.middleware.request_id import RequestIDMiddleware
from app.utils.database import engine
from app.utils.response import (
    error_response,
    validation_error_response,
    make_request_id,
)
# import routers
from app.routers import product, auth, cart, order, admin, customer, payment

app = FastAPI(title="E-Commerce API")

UPLOAD_ROOT = Path(__file__).resolve().parent / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

# mount API router prefix /api/v1
from fastapi import APIRouter
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(product.router)
api_router.include_router(cart.router)
api_router.include_router(order.router)
api_router.include_router(admin.router)
api_router.include_router(customer.router)
api_router.include_router(payment.router)
app.include_router(api_router)

# health
@app.get("/api/health")
def health_check():
    database_ok = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "api": True,
        "database": database_ok,
    }

# root
@app.get("/")
def root():
    return {"message": "FastAPI E-COMMERCE started successfully 🚀"}

# add middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
