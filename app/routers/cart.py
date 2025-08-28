import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.utils.database import SessionLocal
from app.models.cart import Cart as CartModel, CartItem as CartItemModel
from app.schemas.cart import Cart, CartCreate, CartItem, CartItemCreate, CartItemUpdate

API_URL = "/carts"
router = APIRouter(prefix=API_URL, tags=["Carts"])

# DB session dependency
def get_db(): 
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- CART ----------------

# Get all carts (debug/admin purpose)
@router.get("/", response_model=List[Cart])
def read_carts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(CartModel).offset(skip).limit(limit).all()


# Create new cart (user_id OR session_token)
@router.post("/", response_model=Cart, status_code=201)
def create_cart(cart: CartCreate, db: Session = Depends(get_db)):
    db_cart = CartModel(user_id=cart.user_id, session_token=cart.session_token)
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    return db_cart


# Get cart detail (by id)
@router.get("/{cart_id}", response_model=Cart)
def read_cart(cart_id: str, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart


# Delete cart
@router.delete("/{cart_id}")
def delete_cart(cart_id: str, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    db.delete(cart)
    db.commit()
    return {"message": "Cart deleted successfully"}


# ---------------- CART ITEMS ----------------

# Add item to cart
@router.post("/{cart_id}/items", response_model=CartItem, status_code=201)
def add_item(cart_id: str, item: CartItemCreate, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    db_item = CartItemModel(
        cart_id=cart_id,
        product_id=item.product_id,
        quantity=item.quantity
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


# Update item quantity
@router.put("/{cart_id}/items/{item_id}", response_model=CartItem)
def update_item(cart_id: str, item_id: str, item: CartItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(CartItemModel).filter(
        CartItemModel.id == item_id,
        CartItemModel.cart_id == cart_id
    ).first()

    if not db_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if item.quantity is not None:
        db_item.quantity = item.quantity

    db.commit()
    db.refresh(db_item)
    return db_item


# Remove item
@router.delete("/{cart_id}/items/{item_id}")
def delete_item(cart_id: str, item_id: str, db: Session = Depends(get_db)):
    db_item = db.query(CartItemModel).filter(
        CartItemModel.id == item_id,
        CartItemModel.cart_id == cart_id
    ).first()

    if not db_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(db_item)
    db.commit()
    return {"message": "Item removed successfully"}
