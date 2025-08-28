import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base


class Cart(Base):
    __tablename__ = "carts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    session_token = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cart id={self.id} user_id={self.user_id} token={self.session_token}>"


class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    cart_id = Column(String, ForeignKey("carts.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)


    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

    def __repr__(self):
        return f"<CartItem id={self.id} cart_id={self.cart_id} product_id={self.product_id} qty={self.quantity}>"
