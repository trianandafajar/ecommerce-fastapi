import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base
from datetime import datetime


class UserRole(str, enum.Enum):
    admin = "admin"
    customer = "customer"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(225), nullable=False, index=True)
    email = Column(String(225), nullable=False, unique=True, index=True)
    password = Column(Text, nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), nullable=False, default=UserRole.customer.value, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    carts = relationship("Cart", back_populates="user")
    orders = relationship("Order", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} name={self.name} email={self.email} role={self.role}>"
