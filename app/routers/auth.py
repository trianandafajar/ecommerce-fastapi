# app/routers/auth.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer


from app.utils.database import SessionLocal
from app.models import User as UserModel
from app.schemas import User, UserCreate
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response

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
@router.post(
    "/login",
    response_model=SuccessResponse[dict],
    responses={401: {"model": ErrorResponse}},
)
def login(request: Request, email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user or not verify_password(password, user.password):
        return error_response(
            message="Invalid credentials",
            code=401,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    token = create_access_token({"sub": str(user.id)})

    payload = {
        "code": 200,
        "status": "success",
        "message": "Login successful",
        "data": {"access_token": token, "token_type": "bearer"},
        "metadata": {"request_id": getattr(request.state, "request_id", None)},
    }
    return jsonable_encoder(payload)

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