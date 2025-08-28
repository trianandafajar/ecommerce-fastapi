import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(225), nullable=False, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(Text, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    carts = relationship("Cart", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} name={self.name} email={self.email}>"