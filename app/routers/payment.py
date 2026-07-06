import os
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.models import Order as OrderModel, OrderItem as OrderItemModel, User as UserModel
from app.models.order import OrderStatus, PaymentMethod
from app.schemas.response import ErrorResponse, SuccessResponse
from app.utils.auth import require_customer
from app.utils.database import SessionLocal
from app.utils.response import error_response, success_response
from app.utils.stripe_client import get_frontend_url, get_stripe_client

API_URL = "/payment"
router = APIRouter(prefix=API_URL, tags=["Payments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class StripeCheckoutSessionCreate(BaseModel):
    order_id: str
    success_url: str | None = None
    cancel_url: str | None = None


def _load_order(db: Session, order_id: str, user_id: str) -> OrderModel | None:
    return (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.product))
        .filter(OrderModel.id == order_id, OrderModel.user_id == user_id)
        .first()
    )


@router.post(
    "/stripe/checkout-session",
    response_model=SuccessResponse[dict],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def create_stripe_checkout_session(
    request: Request,
    payload: StripeCheckoutSessionCreate,
    db: Session = Depends(get_db),
    current_customer: UserModel = Depends(require_customer),
):
    try:
        stripe_client = get_stripe_client()
    except RuntimeError as config_error:
        return error_response(
            message=str(config_error),
            code=500,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    order = _load_order(db, payload.order_id, str(current_customer.id))
    if not order:
        return error_response(
            message="Order not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    current_payment_method = getattr(order.payment_method, "value", order.payment_method)
    if current_payment_method != PaymentMethod.stripe.value:
        return error_response(
            message="Order payment method is not Stripe",
            code=400,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    if not order.items:
        return error_response(
            message="Order has no items",
            code=400,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    currency = os.getenv("STRIPE_CURRENCY", "usd").lower()
    line_items = []
    for item in order.items:
        product = item.product
        unit_amount = int(Decimal(str(item.price)) * 100)
        price_data = {
            "currency": currency,
            "product_data": {
                "name": product.name if product else f"Product {item.product_id}",
            },
            "unit_amount": unit_amount,
        }
        if product and product.description:
            price_data["product_data"]["description"] = product.description
        if product and product.image_url:
            price_data["product_data"]["images"] = [product.image_url]

        line_items.append(
            {
                "price_data": price_data,
                "quantity": int(item.quantity),
            }
        )

    success_url = payload.success_url or get_frontend_url(
        f"/my/orders/{order.id}?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel_url = payload.cancel_url or get_frontend_url(
        f"/my/orders/{order.id}?payment=cancelled"
    )

    session = stripe_client.checkout.Session.create(
        mode="payment",
        customer_email=current_customer.email,
        line_items=line_items,
        metadata={
            "order_id": str(order.id),
            "user_id": str(current_customer.id),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    order.payment_provider = "stripe"
    order.stripe_checkout_session_id = session.id
    order.stripe_payment_intent_id = getattr(session, "payment_intent", None)
    order.stripe_customer_id = getattr(session, "customer", None)
    db.commit()

    return success_response(
        data={
            "id": session.id,
            "url": session.url,
            "order_id": str(order.id),
        },
        message="Stripe checkout session created",
        code=201,
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        stripe_client = get_stripe_client()
    except RuntimeError as config_error:
        return JSONResponse(status_code=500, content={"message": str(config_error)})

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not signature or not webhook_secret:
        return JSONResponse(status_code=400, content={"message": "Missing stripe webhook secret"})

    try:
        event = stripe_client.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
    except ValueError:
        return JSONResponse(status_code=400, content={"message": "Invalid payload"})
    except stripe_client.error.SignatureVerificationError:
        return JSONResponse(status_code=400, content={"message": "Invalid signature"})

    event_type = event["type"]
    data_object = event["data"]["object"]

    def mark_order_paid(order: OrderModel | None):
        if not order:
            return

        order.status = OrderStatus.paid
        order.payment_method = PaymentMethod.stripe
        order.payment_provider = "stripe"
        order.stripe_checkout_session_id = data_object.get("id") or order.stripe_checkout_session_id
        order.stripe_payment_intent_id = data_object.get("payment_intent") or order.stripe_payment_intent_id
        order.stripe_customer_id = data_object.get("customer") or order.stripe_customer_id
        db.commit()

    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        session_id = data_object.get("id")
        order = None
        if session_id:
            order = db.query(OrderModel).filter(OrderModel.stripe_checkout_session_id == session_id).first()
        if not order:
            order_id = data_object.get("metadata", {}).get("order_id")
            if order_id:
                order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        mark_order_paid(order)

    if event_type == "payment_intent.succeeded":
        payment_intent_id = data_object.get("id")
        order = None
        if payment_intent_id:
            order = db.query(OrderModel).filter(OrderModel.stripe_payment_intent_id == payment_intent_id).first()
        if not order:
            order_id = data_object.get("metadata", {}).get("order_id")
            if order_id:
                order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        mark_order_paid(order)

    return JSONResponse(status_code=200, content={"received": True})
