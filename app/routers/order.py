from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from decimal import Decimal

from app.utils.database import SessionLocal
from app.models import Order as OrderModel, OrderItem as OrderItemModel, User as UserModel
from app.schemas.order import Order as OrderSchema, OrderCreate as OrderCreateSchema
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response
from app.utils.email import send_email
from app.utils.templates.checkout_email import build_checkout_email
from app.utils.auth import get_current_user, require_customer


API_URL = "/orders"
router = APIRouter(prefix=API_URL, tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_order(db: Session, order_id: str, user_id: str | None = None):
    query = db.query(OrderModel).options(
        joinedload(OrderModel.items).joinedload(OrderItemModel.product)
    ).filter(OrderModel.id == order_id)
    if user_id:
        query = query.filter(OrderModel.user_id == user_id)
    return query.first()


def _serialize_order(order: OrderModel) -> dict:
    return OrderSchema.model_validate(order).model_dump()


@router.get(
    "/",
    response_model=SuccessResponse[List[OrderSchema]],
    responses={500: {"model": ErrorResponse}},
)
def read_orders(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    status_value: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        query = (
            db.query(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
            .order_by(OrderModel.created_at.desc())
        )

        if current_user.role != "admin":
            query = query.filter(OrderModel.user_id == str(current_user.id))

        if status_value:
            query = query.filter(OrderModel.status == status_value)

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


# Create order
@router.post(
    "/",
    response_model=SuccessResponse[OrderSchema],
    responses={400: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    request: Request,
    order: OrderCreateSchema,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_customer),
):
    if not order.items:
        return error_response(
            message="Order items cannot be empty",
            code=400,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    try:
        total_amount = sum((item.price * item.quantity for item in order.items), start=Decimal("0"))

        db_order = OrderModel(
            user_id=current_user.id,
            payment_method=order.payment_method,
            first_name=order.first_name,
            last_name=order.last_name,
            address=order.address,
            city=order.city,
            postal_code=order.postal_code,
            phone=order.phone,
            total_amount=total_amount,
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        for item in order.items:
            db_item = OrderItemModel(
                order_id=str(db_order.id),
                product_id=str(item.product_id),
                quantity=item.quantity,
                price=item.price,
            )
            db.add(db_item)

        db.commit()
        db_order = _load_order(db, str(db_order.id), str(current_user.id))
        if not db_order:
            raise ValueError("Failed to reload created order")

        try:
            html_body = build_checkout_email(db_order)
            if current_user.email:
                send_email(
                    to_email=current_user.email,
                    subject="Your Order Confirmation - React Market",
                    html_body=html_body,
                )
        except Exception as mail_error:
            print(f"[WARNING] Failed to send checkout email: {mail_error}")

        return success_response(
            data=_serialize_order(db_order),
            message="Order created successfully",
            code=201,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to create order",
            code=400,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


@router.get(
    "/me",
    response_model=SuccessResponse[List[OrderSchema]],
    responses={500: {"model": ErrorResponse}},
)
def read_my_orders(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_customer),
):
    try:
        orders = (
            db.query(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
            .filter(OrderModel.user_id == str(current_user.id))
            .order_by(OrderModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return success_response(
            data=[_serialize_order(order) for order in orders],
            message="My orders fetched successfully",
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch my orders",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


@router.get(
    "/{order_id}",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def read_my_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_customer),
):
    order = _load_order(db, order_id, str(current_user.id))
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
    "/{order_id}/track",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def track_my_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_customer),
):
    order = _load_order(db, order_id, str(current_user.id))
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
