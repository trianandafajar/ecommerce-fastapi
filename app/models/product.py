import uuid
from sqlalchemy import Column, String, Text, DECIMAL, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.database import Base

class Product(Base):
    __tablename__  = "products"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(225), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(DECIMAL(12, 2), nullable=False)
    image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    order_items = relationship("OrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product id={self.id} name={self.name} price={self.price}>"
