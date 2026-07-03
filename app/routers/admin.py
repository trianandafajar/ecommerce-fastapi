from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.utils.database import SessionLocal
from app.models import Order as OrderModel, OrderItem as OrderItemModel, User as UserModel
from app.models.order import OrderStatus
from app.schemas.order import Order as OrderSchema, OrderStatusUpdate
from app.schemas.user import User as UserSchema, AdminUserUpdate
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response
from app.utils.auth import require_admin


API_URL = "/admin"
router = APIRouter(prefix=API_URL, tags=["Admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_order(db: Session, order_id: str):
    return (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
        .filter(OrderModel.id == order_id)
        .first()
    )


def _serialize_order(order: OrderModel) -> dict:
    return OrderSchema.model_validate(order).model_dump()


def _serialize_user(user: UserModel) -> dict:
    return UserSchema.model_validate(user).model_dump()


def _apply_order_status(
    order_id: str,
    new_status: OrderStatus,
    request: Request,
    db: Session,
):
    order = _load_order(db, order_id)
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    order = _load_order(db, order_id)

    return success_response(
        data=_serialize_order(order),
        message="Order status updated successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.get(
    "/customers",
    response_model=SuccessResponse[List[UserSchema]],
    responses={500: {"model": ErrorResponse}},
)
def list_customers(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    try:
        customers = (
            db.query(UserModel)
            .filter(UserModel.role == "customer")
            .order_by(UserModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return success_response(
            data=[_serialize_user(user) for user in customers],
            message="Customers fetched successfully",
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch customers",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


@router.get(
    "/customers/{customer_id}",
    response_model=SuccessResponse[UserSchema],
    responses={404: {"model": ErrorResponse}},
)
def read_customer(
    customer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    customer = (
        db.query(UserModel)
        .filter(UserModel.id == customer_id, UserModel.role == "customer")
        .first()
    )
    if not customer:
        return error_response(
            message="Customer not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    return success_response(
        data=_serialize_user(customer),
        message="Customer fetched successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.put(
    "/customers/{customer_id}",
    response_model=SuccessResponse[UserSchema],
    responses={404: {"model": ErrorResponse}},
)
def update_customer(
    customer_id: str,
    payload: AdminUserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    customer = (
        db.query(UserModel)
        .filter(UserModel.id == customer_id, UserModel.role == "customer")
        .first()
    )
    if not customer:
        return error_response(
            message="Customer not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    if payload.name is not None:
        customer.name = payload.name
    if payload.phone is not None:
        customer.phone = payload.phone
    if payload.email is not None:
        existing = (
            db.query(UserModel)
            .filter(UserModel.email == payload.email, UserModel.id != customer.id)
            .first()
        )
        if existing:
            return error_response(
                message="Email already registered",
                code=400,
                metadata={"request_id": getattr(request.state, "request_id", None)},
            )
        customer.email = payload.email
    if payload.is_active is not None:
        customer.is_active = payload.is_active

    db.commit()
    db.refresh(customer)

    return success_response(
        data=_serialize_user(customer),
        message="Customer updated successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.get(
    "/orders",
    response_model=SuccessResponse[List[OrderSchema]],
    responses={500: {"model": ErrorResponse}},
)
def list_orders(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    status_value: OrderStatus | None = None,
    customer_id: str | None = None,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    try:
        query = (
            db.query(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
            .order_by(OrderModel.created_at.desc())
        )
        if status_value:
            query = query.filter(OrderModel.status == status_value)
        if customer_id:
            query = query.filter(OrderModel.user_id == customer_id)

        orders = query.offset(skip).limit(limit).all()
        return success_response(
            data=[_serialize_order(order) for order in orders],
            message="Orders fetched successfully",
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch orders",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


@router.get(
    "/orders/{order_id}",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def read_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    order = _load_order(db, order_id)
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    return success_response(
        data=_serialize_order(order),
        message="Order fetched successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.get(
    "/orders/{order_id}/track",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def track_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    order = _load_order(db, order_id)
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    return success_response(
        data=_serialize_order(order),
        message="Order tracking fetched successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.put(
    "/orders/{order_id}/status",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
@router.patch(
    "/orders/{order_id}/status",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    return _apply_order_status(order_id, payload.status, request, db)


@router.post(
    "/orders/{order_id}/approve",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def approve_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    return _apply_order_status(order_id, OrderStatus.paid, request, db)


@router.post(
    "/orders/{order_id}/reject",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def reject_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    return _apply_order_status(order_id, OrderStatus.cancelled, request, db)
