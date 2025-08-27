import uuid
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None

class Product(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
