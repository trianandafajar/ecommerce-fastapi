# app/utils/auto_wrap.py
import inspect
from functools import wraps
from typing import Any, Callable, Optional
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.utils.response import success_response

def _is_wrapped_payload(obj: Any) -> bool:
    return isinstance(obj, dict) and "code" in obj and "status" in obj

def auto_wrap_response(message: Optional[str] = None, code: int = 200):
    """
    Decorator untuk otomatis bungkus return value jadi success_response,
    kecuali jika fungsi sudah mengembalikan JSONResponse atau payload sudah wrapper.
    """
    def decorator(func: Callable):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def _async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                if isinstance(result, JSONResponse):
                    return result
                if _is_wrapped_payload(result):
                    # already wrapper
                    return JSONResponse(status_code=result.get("code", 200), content=jsonable_encoder(result))
                # otherwise wrap
                return success_response(data=result, message=message or "Success", code=code)
            return _async_wrapper
        else:
            @wraps(func)
            def _sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if isinstance(result, JSONResponse):
                    return result
                if _is_wrapped_payload(result):
                    return JSONResponse(status_code=result.get("code", 200), content=jsonable_encoder(result))
                return success_response(data=result, message=message or "Success", code=code)
            return _sync_wrapper
    return decorator
