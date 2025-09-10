# app/schemas/cart.py
import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# ---------------- CART ITEM ----------------
class CartItemBase(BaseModel):
    product_id: uuid.UUID
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = None

class CartItem(CartItemBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


# ---------------- CART ----------------
class CartBase(BaseModel):
    user_id: Optional[uuid.UUID] = None  # boleh kosong (guest cart)

class CartCreate(CartBase):
    pass

class Cart(CartBase):
    id: uuid.UUID
    created_at: datetime
    items: List[CartItem] = []

    class Config:
        from_attributes = True
