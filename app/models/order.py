import uuid
from sqlalchemy import Column, String, ForeignKey, Enum, DECIMAL, Text, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.utils.database import Base

# enum layer
class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    completed = "completed"
    cancelled = "cancelled"
    
class PaymentMethod(str, enum.Enum):
    cod = "cod"
    bank_transfer = "bank_transfer"
    
# schema
class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    total_amount = Column(DECIMAL(12, 2), nullable=False)

    # shipping info
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    address = Column(Text, nullable=False)
    city = Column(String(50), nullable=False)
    postal_code = Column(String(20), nullable=False)
    phone = Column(String(20), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    user = relationship("User", back_populates="orders")
    
    def __repr__(self):
        return f"<Order id={self.id} user_id={self.user_id} status={self.status}>"
    
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem id={self.id} order_id={self.order_id} product_id={self.product_id}>"
