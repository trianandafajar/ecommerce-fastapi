from fastapi import APIRouter, Depends, Request, status
from fastapi import Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import List
from datetime import date, datetime, time, timedelta

from app.utils.database import SessionLocal
from app.models import Order as OrderModel, OrderItem as OrderItemModel, Product as ProductModel, User as UserModel
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


def _format_currency(value) -> str:
    amount = float(value or 0)
    return f"${amount:,.0f}"


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
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="Search by name, email, or phone"),
    status_value: str | None = Query(None, description="Filter by active/inactive status"),
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    try:
        query = db.query(UserModel).filter(UserModel.role == "customer")

        if search:
            like_search = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    UserModel.name.ilike(like_search),
                    UserModel.email.ilike(like_search),
                    UserModel.phone.ilike(like_search),
                )
            )

        if status_value in {"active", "inactive"}:
            query = query.filter(UserModel.is_active == (status_value == "active"))

        total = query.count()
        total_pages = max((total + per_page - 1) // per_page, 1) if total else 0
        offset = (page - 1) * per_page

        customers = (
            query.order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return success_response(
            data=[_serialize_user(user) for user in customers],
            message="Customers fetched successfully",
            metadata={
                "request_id": getattr(request.state, "request_id", None),
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
                "filters": {
                    "search": search,
                    "status_value": status_value,
                },
            },
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch customers",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


@router.get(
    "/dashboard",
    response_model=SuccessResponse[dict],
    responses={500: {"model": ErrorResponse}},
)
def dashboard_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    try:
        now = datetime.utcnow()
        month_keys = []
        for index in range(5, -1, -1):
            marker = (now.replace(day=1) - timedelta(days=32 * index)).replace(day=1)
            month_keys.append((marker.year, marker.month))

        total_customers = db.query(func.count(UserModel.id)).filter(UserModel.role == "customer").scalar() or 0
        active_customers = (
            db.query(func.count(UserModel.id))
            .filter(UserModel.role == "customer", UserModel.is_active.is_(True))
            .scalar()
            or 0
        )

        total_orders = db.query(func.count(OrderModel.id)).scalar() or 0
        pending_orders = (
            db.query(func.count(OrderModel.id))
            .filter(OrderModel.status == OrderStatus.pending)
            .scalar()
            or 0
        )
        paid_orders = (
            db.query(func.count(OrderModel.id))
            .filter(OrderModel.status == OrderStatus.paid)
            .scalar()
            or 0
        )
        shipped_orders = (
            db.query(func.count(OrderModel.id))
            .filter(OrderModel.status == OrderStatus.shipped)
            .scalar()
            or 0
        )
        completed_orders = (
            db.query(func.count(OrderModel.id))
            .filter(OrderModel.status == OrderStatus.completed)
            .scalar()
            or 0
        )
        cancelled_orders = (
            db.query(func.count(OrderModel.id))
            .filter(OrderModel.status == OrderStatus.cancelled)
            .scalar()
            or 0
        )
        revenue = (
            db.query(func.coalesce(func.sum(OrderModel.total_amount), 0))
            .filter(OrderModel.status == OrderStatus.completed)
            .scalar()
            or 0
        )

        recent_orders = (
            db.query(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product), joinedload(OrderModel.user))
            .order_by(OrderModel.created_at.desc())
            .limit(5)
            .all()
        )

        recent_month_orders = (
            db.query(OrderModel.created_at, OrderModel.total_amount, OrderModel.status)
            .order_by(OrderModel.created_at.desc())
            .all()
        )

        completed_by_month = {key: 0.0 for key in month_keys}
        orders_by_month = {key: 0 for key in month_keys}
        for created_at, total_amount, status in recent_month_orders:
            if not created_at:
                continue
            created = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
            key = (created.year, created.month)
            if key not in completed_by_month:
                continue
            orders_by_month[key] += 1
            if getattr(status, "value", status) == OrderStatus.completed.value:
                completed_by_month[key] += float(total_amount or 0)

        monthly_revenue = [
            {
                "label": datetime(year, month, 1).strftime("%b"),
                "value": round(completed_by_month[(year, month)]),
                "orders": orders_by_month[(year, month)],
            }
            for year, month in month_keys
        ]

        status_total = total_orders or 1
        status_breakdown = [
            {
                "label": label.capitalize(),
                "value": count,
                "share": round((count / status_total) * 100) if total_orders else 0,
                "accent": accent,
            }
            for label, count, accent in [
                ("pending", pending_orders, "bg-amber-500"),
                ("paid", paid_orders, "bg-cyan-500"),
                ("shipped", shipped_orders, "bg-sky-500"),
                ("completed", completed_orders, "bg-emerald-500"),
                ("cancelled", cancelled_orders, "bg-rose-500"),
            ]
        ]

        product_category_counts = (
            db.query(ProductModel.category, func.count(ProductModel.id))
            .filter(ProductModel.category.isnot(None))
            .filter(ProductModel.category != "")
            .group_by(ProductModel.category)
            .order_by(func.count(ProductModel.id).desc())
            .limit(6)
            .all()
        )
        top_categories = [
            {
                "label": category,
                "value": count,
            }
            for category, count in product_category_counts
        ]

        total_orders_safe = total_orders or 1
        order_stages = [
            {
                "label": "Pending",
                "value": round((pending_orders / total_orders_safe) * 100) if total_orders else 0,
                "accent": "bg-amber-500",
            },
            {
                "label": "Paid",
                "value": round((paid_orders / total_orders_safe) * 100) if total_orders else 0,
                "accent": "bg-cyan-500",
            },
            {
                "label": "Shipped",
                "value": round((shipped_orders / total_orders_safe) * 100) if total_orders else 0,
                "accent": "bg-sky-500",
            },
            {
                "label": "Completed",
                "value": round((completed_orders / total_orders_safe) * 100) if total_orders else 0,
                "accent": "bg-emerald-500",
            },
            {
                "label": "Cancelled",
                "value": round((cancelled_orders / total_orders_safe) * 100) if total_orders else 0,
                "accent": "bg-rose-500",
            },
        ]

        open_orders = pending_orders + paid_orders
        risk_orders = pending_orders + cancelled_orders
        completion_rate = round((completed_orders / total_orders_safe) * 100) if total_orders else 0
        active_rate = round((active_customers / (total_customers or 1)) * 100) if total_customers else 0

        latest_handoff = (
            f"{paid_orders} orders are paid and ready for fulfillment."
            if paid_orders
            else "No paid orders are waiting for handoff."
        )

        metrics = [
            {
                "label": "Active customers",
                "value": f"{active_customers:,}",
                "delta": f"{active_rate}% active",
                "tone": "emerald",
                "note": f"{total_customers:,} customer accounts in total",
            },
            {
                "label": "Open orders",
                "value": f"{open_orders:,}",
                "delta": f"{completion_rate}% completed",
                "tone": "cyan",
                "note": "Pending + paid orders awaiting action",
            },
            {
                "label": "Revenue",
                "value": _format_currency(revenue),
                "delta": f"{completed_orders:,} completed",
                "tone": "amber",
                "note": "Completed orders only",
            },
            {
                "label": "At-risk orders",
                "value": f"{risk_orders:,}",
                "delta": f"{cancelled_orders:,} cancelled",
                "tone": "rose",
                "note": "Pending or cancelled orders need attention",
            },
        ]

        return success_response(
            data={
                "metrics": metrics,
                "order_stages": order_stages,
                "recent_orders": [
                    {
                        "id": order.id,
                        "customer": (
                            order.user.name
                            if getattr(order, "user", None) and order.user
                            else f"{order.first_name or ''} {order.last_name or ''}".strip() or "Guest"
                        ),
                        "email": order.user.email if getattr(order, "user", None) and order.user else "",
                        "amount": _format_currency(order.total_amount),
                        "status": order.status.value if hasattr(order.status, "value") else str(order.status),
                        "updatedAt": order.updated_at or order.created_at,
                    }
                    for order in recent_orders
                ],
                "summary": {
                    "queue": pending_orders,
                    "sla": completion_rate,
                    "risk": risk_orders,
                    "latest_handoff": latest_handoff,
                },
                "charts": {
                    "monthly_revenue": monthly_revenue,
                    "status_breakdown": status_breakdown,
                    "top_categories": top_categories,
                },
            },
            message="Dashboard summary fetched successfully",
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch dashboard summary",
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
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status_value: OrderStatus | None = None,
    customer_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(require_admin),
):
    try:
        if start_date and end_date and start_date > end_date:
            return error_response(
                message="start_date cannot be later than end_date",
                code=400,
                metadata={"request_id": getattr(request.state, "request_id", None)},
            )

        query = (
            db.query(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
            .order_by(OrderModel.created_at.desc())
        )
        if search:
            like_search = f"%{search.strip()}%"
            query = query.outerjoin(UserModel, OrderModel.user_id == UserModel.id).filter(
                or_(
                    OrderModel.id.ilike(like_search),
                    OrderModel.first_name.ilike(like_search),
                    OrderModel.last_name.ilike(like_search),
                    OrderModel.address.ilike(like_search),
                    OrderModel.city.ilike(like_search),
                    OrderModel.phone.ilike(like_search),
                    UserModel.name.ilike(like_search),
                    UserModel.email.ilike(like_search),
                )
            )
        if status_value:
            query = query.filter(OrderModel.status == status_value)
        if customer_id:
            query = query.filter(OrderModel.user_id == customer_id)
        if start_date:
            query = query.filter(OrderModel.created_at >= datetime.combine(start_date, time.min))
        if end_date:
            query = query.filter(OrderModel.created_at <= datetime.combine(end_date, time.max))

        total = query.count()
        total_pages = max((total + per_page - 1) // per_page, 1) if total else 0
        offset = (page - 1) * per_page

        orders = query.offset(offset).limit(per_page).all()
        return success_response(
            data=[_serialize_order(order) for order in orders],
            message="Orders fetched successfully",
            metadata={
                "request_id": getattr(request.state, "request_id", None),
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
                "filters": {
                    "status_value": status_value,
                    "customer_id": customer_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "search": search,
                },
            },
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
