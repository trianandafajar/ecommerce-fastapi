from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List

from app.models import Order as OrderModel, OrderItem as OrderItemModel, Product as ProductModel, User as UserModel
from app.models.order import OrderStatus
from app.schemas import Order as OrderSchema, Product as ProductSchema
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.auth import require_customer
from app.utils.database import SessionLocal
from app.utils.response import success_response, error_response

API_URL = "/customer"
router = APIRouter(prefix=API_URL, tags=["Customer"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_order(order: OrderModel) -> dict:
    return OrderSchema.model_validate(order).model_dump()


def _serialize_product(product: ProductModel) -> dict:
    return ProductSchema.model_validate(product).model_dump()


@router.get(
    "/dashboard",
    response_model=SuccessResponse[dict],
    responses={500: {"model": ErrorResponse}},
)
def customer_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: UserModel = Depends(require_customer),
):
    try:
        order_query = (
            db.query(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
            .filter(OrderModel.user_id == str(current_customer.id))
            .order_by(OrderModel.created_at.desc())
        )

        total_orders = order_query.count()
        active_orders = (
            db.query(func.count(OrderModel.id))
            .filter(
                OrderModel.user_id == str(current_customer.id),
                OrderModel.status == OrderStatus.pending,
            )
            .scalar()
            or 0
        )
        completed_orders = (
            db.query(func.count(OrderModel.id))
            .filter(
                OrderModel.user_id == str(current_customer.id),
                OrderModel.status == OrderStatus.completed,
            )
            .scalar()
            or 0
        )
        cancelled_orders = (
            db.query(func.count(OrderModel.id))
            .filter(
                OrderModel.user_id == str(current_customer.id),
                OrderModel.status == OrderStatus.cancelled,
            )
            .scalar()
            or 0
        )
        total_spent = (
            db.query(func.coalesce(func.sum(OrderModel.total_amount), 0))
            .filter(
                OrderModel.user_id == str(current_customer.id),
                OrderModel.status.in_(
                    [OrderStatus.paid, OrderStatus.shipped, OrderStatus.completed]
                ),
            )
            .scalar()
            or 0
        )

        tracking_order = order_query.filter(OrderModel.status == OrderStatus.pending).first()
        latest_order = order_query.first()
        if not tracking_order:
            tracking_order = latest_order
        recent_orders = order_query.limit(5).all()
        featured_products = (
            db.query(ProductModel)
            .order_by(ProductModel.created_at.desc())
            .limit(4)
            .all()
        )

        return success_response(
            data={
                "summary": {
                    "total_orders": total_orders,
                    "active_orders": active_orders,
                    "completed_orders": completed_orders,
                    "cancelled_orders": cancelled_orders,
                    "total_spent": str(total_spent),
                },
                "tracking_order": _serialize_order(tracking_order) if tracking_order else None,
                "latest_order": _serialize_order(latest_order) if latest_order else None,
                "recent_orders": [_serialize_order(order) for order in recent_orders],
                "featured_products": [
                    _serialize_product(product) for product in featured_products
                ],
            },
            message="Customer dashboard fetched successfully",
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch customer dashboard",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
