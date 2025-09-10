# app/routers/auth.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer


from app.utils.database import SessionLocal
from app.models import User as UserModel, OTP
from app.schemas import User, UserCreate, ForgotPasswordRequest, ResetPasswordRequest, VerifyOTPRequest, LoginRequest
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.otp import generate_otp, send_otp_email
from app.utils.response import success_response, error_response

import datetime

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# REGISTER
@router.post(
    "/register",
    response_model=SuccessResponse[User],
    responses={400: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        return error_response(
            message="Email already registered",
            code=400,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    try:
        new_user = UserModel(
            name=user.name,
            email=user.email,
            phone=user.phone,
            password=hash_password(user.password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        payload = {
            "code": 201,
            "status": "success",
            "message": "User registered successfully",
            "data": User.model_validate(new_user).model_dump(),
            "metadata": {"request_id": getattr(request.state, "request_id", None)},
        }
        return jsonable_encoder(payload)
    except Exception as e:
        return error_response(
            message="Failed to register user",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


# LOGIN
@router.post("/login")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        return error_response(
            message="Invalid credentials",
            code=401,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    token = create_access_token({"sub": str(user.id)})

    return {
        "code": 200,
        "status": "success",
        "message": "Login successful",
        "data": {"access_token": token, "token_type": "bearer"},
        "metadata": {"request_id": getattr(request.state, "request_id", None)},
    }

# GET CURRENT USER
@router.get(
    "/me",
    response_model=SuccessResponse[dict],
    responses={401: {"model": ErrorResponse}},
)
def me(request: Request, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        user = get_current_user(token, db)
        if not user:
            return error_response(
                message="Unauthorized",
                code=401,
                metadata={"request_id": getattr(request.state, "request_id", None)},
            )

        payload = {
            "code": 200,
            "status": "success",
            "message": "User info retrieved successfully",
            "data": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
            },
            "metadata": {"request_id": getattr(request.state, "request_id", None)},
        }
        return jsonable_encoder(payload)

    except Exception as e:
        return error_response(
            message="Failed to get user info",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
        
@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user:
        return error_response(message="Email not found", code=404)

    code = generate_otp(db, str(user.id))
    send_otp_email(user.email, code)

    return success_response(message="OTP sent to email", data={})

@router.post("/verify-otp")
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user:
        return error_response(message="User not found", code=404)

    otp = (
        db.query(OTP)
        .filter(
            OTP.user_id == str(user.id),
            OTP.code == payload.code,
            OTP.is_used == False,
            OTP.expires_at > datetime.datetime.utcnow(),
        )
        .first()
    )
    
    otp.is_used = True
    db.commit()

    if not otp:
        return error_response(message="Invalid or expired OTP", code=400)

    return success_response(message="OTP verified", data={})

# RESET PASSWORD
@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user:
        return error_response(message="User not found", code=404)

    user.password = hash_password(payload.new_password)
    db.commit()

    return success_response(message="Password reset successful", data={})