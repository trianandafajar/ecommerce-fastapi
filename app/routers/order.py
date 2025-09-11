from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from typing import List

from app.utils.database import SessionLocal
from app.models import Order as OrderModel, OrderItem as OrderItemModel, User as UserModel
from app.schemas.order import Order as OrderSchema, OrderCreate as OrderCreateSchema
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response
from app.utils.email import send_email
from app.utils.templates.checkout_email import build_checkout_email
from app.utils.auth import get_current_user


API_URL = "/orders"
router = APIRouter(prefix=API_URL, tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    current_user: UserModel = Depends(get_current_user),
):
    try:
        total_amount = sum([item.price * item.quantity for item in order.items])

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
        db.refresh(db_order)
        
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
            data=OrderSchema.model_validate(db_order).model_dump(),
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


# Get all orders
@router.get(
    "/",
    response_model=SuccessResponse[List[OrderSchema]],
    responses={500: {"model": ErrorResponse}},
)
def read_orders(request: Request, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        orders = db.query(OrderModel).offset(skip).limit(limit).all()
        return success_response(
            data=[OrderSchema.model_validate(o).model_dump() for o in orders],
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


# Get order detail
@router.get(
    "/{order_id}",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def read_order(order_id: str, request: Request, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    return success_response(
        data=OrderSchema.model_validate(order).model_dump(),
        message="Order fetched successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


# Update order status
@router.put(
    "/{order_id}/status",
    response_model=SuccessResponse[OrderSchema],
    responses={404: {"model": ErrorResponse}},
)
def update_order_status(order_id: str, status_value: str, request: Request, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    order.status = status_value
    db.commit()
    db.refresh(order)

    return success_response(
        data=OrderSchema.model_validate(order).model_dump(),
        message="Order status updated successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


# Delete order
@router.delete(
    "/{order_id}",
    response_model=SuccessResponse[dict],
    responses={404: {"model": ErrorResponse}},
)
def delete_order(order_id: str, request: Request, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    db.delete(order)
    db.commit()

    return success_response(
        data={"deleted_id": order_id},
        message="Order deleted successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )
