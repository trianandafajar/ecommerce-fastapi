# app/schemas/order.py
import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from app.models.order import OrderStatus, PaymentMethod


# ---------------- ORDER ITEM ----------------
class OrderItemBase(BaseModel):
    product_id: uuid.UUID
    quantity: int
    price: Decimal


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


# ---------------- ORDER ----------------
class OrderBase(BaseModel):
    user_id: uuid.UUID = None
    payment_method: PaymentMethod
    shipping_address: str


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class Order(OrderBase):
    id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    items: List[OrderItem] = []

    class Config:
        from_attributes = True
