# app/utils/auth.py
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import os
from typing import Optional, Dict, Any

from fastapi import Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.models import User as UserModel
from app.utils.database import SessionLocal

# config
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "inirahasiatinkatnegara")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
# debug flag (set AUTH_DEBUG=true in env to enable)
AUTH_DEBUG = os.getenv("AUTH_DEBUG", "false").lower() in ("1", "true", "yes")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# keep oauth2_scheme for docs (Swagger) but we will also accept token from cookie
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _debug(*args, **kwargs):
    if AUTH_DEBUG:
        print("[AUTH_DEBUG]", *args, **kwargs)


def _truncate_token(token: str, head: int = 8, tail: int = 6) -> str:
    if not token:
        return "(none)"
    if len(token) <= head + tail + 3:
        return token
    return f"{token[:head]}...{token[-tail:]}"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    - data: claims dict (should include 'sub' as user id)
    - expires_delta: optional override for expiry
    Returns encoded JWT string.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    # include issued-at and expiry as numeric timestamps (standard)
    to_encode.update({"iat": int(now.timestamp()), "exp": int(expire.timestamp())})

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    _debug("Created token (truncated):", _truncate_token(token))
    return token


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode JWT token and return payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        _debug("JWT decode error:", repr(e))
        return None
    except Exception as e:
        _debug("Unexpected error decoding token:", repr(e))
        return None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_token_from_request(request: Request) -> Optional[str]:
    """
    Try to extract token from:
      1. Authorization header: "Bearer <token>"
      2. Cookies: access_token (or token)
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            _debug("Token found in header:", _truncate_token(token))
            return token
        else:
            _debug("Authorization header present but malformed:", auth_header)

    # fallback to cookie (common when front-end stores token in cookie)
    cookie_token = request.cookies.get("access_token") or request.cookies.get("token")
    if cookie_token:
        _debug("Token found in cookie:", _truncate_token(cookie_token))
        return cookie_token

    _debug("No token found in header or cookie")
    return None


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """
    Dependency that returns the current user or None if token missing/invalid.
    Use this on routes where authentication is optional.
    """
    token = _extract_token_from_request(request)
    if not token:
        _debug("get_current_user_optional: no token provided")
        return None

    _debug("Raw token (truncated):", _truncate_token(token))
    payload = decode_access_token(token)
    _debug("Decoded payload:", payload)
    if not payload:
        _debug("Token decode returned no payload (invalid/expired)")
        return None

    user_id = payload.get("sub")
    if not user_id:
        _debug("Token payload missing 'sub' claim:", payload)
        return None

    # user.id is a UUID string in your model; compare as string
    user = db.query(UserModel).filter(UserModel.id == str(user_id)).first()
    _debug("User lookup by sub:", str(user_id), "=>", "FOUND" if user else "NOT FOUND")
    return user


def get_current_user(
    user: Optional[UserModel] = Depends(get_current_user_optional),
) -> UserModel:
    """
    Dependency that ensures the user is authenticated.
    Raises 401 Unauthorized when token is missing/invalid.
    Use this for protected routes (required auth).
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
