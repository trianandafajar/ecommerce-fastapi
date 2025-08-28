# app/middleware/request_id.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.utils.response import make_request_id

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # gunakan header X-Request-ID kalau ada, kalau tidak generate baru
        req_id = request.headers.get("X-Request-ID") or make_request_id()
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
