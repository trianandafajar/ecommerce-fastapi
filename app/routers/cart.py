# app/routers/cart.py
import uuid
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app.utils.database import SessionLocal
from app.models.cart import Cart as CartModel, CartItem as CartItemModel
from app.schemas.cart import (
    Cart as CartSchema,
    CartCreate as CartCreateSchema,
    CartItem as CartItemSchema,
    CartItemCreate as CartItemCreateSchema,
    CartItemUpdate as CartItemUpdateSchema,
)
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response

API_URL = "/api/v1/carts"
router = APIRouter(prefix=API_URL, tags=["Carts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _to_cart_dict(cart_orm: CartModel) -> dict:
    return CartSchema.model_validate(cart_orm).model_dump()


def _to_cart_item_dict(item_orm: CartItemModel) -> dict:
    return CartItemSchema.model_validate(item_orm).model_dump()

@router.get(
    "/",
    response_model=SuccessResponse[List[CartSchema]],
    responses={400: {"model": ErrorResponse}},
)
def read_carts(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    try:
        carts_db = db.query(CartModel).offset(skip).limit(limit).all()
        carts = [ _to_cart_dict(c) for c in carts_db ]

        metadata = {
            "request_id": getattr(request.state, "request_id", None),
            "pagination": {"page": (skip // limit) + 1 if limit else 1, "per_page": limit, "total": len(carts)},
        }

        payload = {
            "code": 200,
            "status": "success",
            "message": "Carts fetched",
            "data": carts,
            "metadata": metadata,
        }
        return jsonable_encoder(payload)
    except Exception as e:
        return error_response(message="Failed to fetch carts", code=500, details=str(e), metadata={"request_id": getattr(request.state, "request_id", None)})


# Create cart
@router.post("/", response_model=SuccessResponse[CartSchema], responses={400: {"model": ErrorResponse}}, status_code=status.HTTP_201_CREATED)
def create_cart(request: Request, cart: CartCreateSchema, db: Session = Depends(get_db)):
    try:
        db_cart = CartModel(user_id=str(cart.user_id) if cart.user_id else None, session_token=cart.session_token)
        db.add(db_cart)
        db.commit()
        db.refresh(db_cart)

        cart_data = _to_cart_dict(db_cart)
        payload = {
            "code": 201,
            "status": "success",
            "message": "Cart created",
            "data": cart_data,
            "metadata": {"request_id": getattr(request.state, "request_id", None)},
        }
        return jsonable_encoder(payload)
    except Exception as e:
        return error_response(message="Failed to create cart", code=500, details=str(e), metadata={"request_id": getattr(request.state, "request_id", None)})


# Get cart detail
@router.get("/{cart_id}", response_model=SuccessResponse[CartSchema], responses={404: {"model": ErrorResponse}})
def read_cart(request: Request, cart_id: str, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        return error_response(message="Cart not found", code=404,
                              metadata={"request_id": getattr(request.state, "request_id", None)})
    payload = {
        "code": 200,
        "status": "success",
        "message": "Cart fetched",
        "data": _to_cart_dict(cart),
        "metadata": {"request_id": getattr(request.state, "request_id", None)},
    }
    return jsonable_encoder(payload)


# Delete cart (return success wrapper)
@router.delete("/{cart_id}", response_model=SuccessResponse[dict], responses={404: {"model": ErrorResponse}})
def delete_cart(request: Request, cart_id: str, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        return error_response(message="Cart not found", code=404,
                              metadata={"request_id": getattr(request.state, "request_id", None)})
    db.delete(cart)
    db.commit()
    payload = {
        "code": 200,
        "status": "success",
        "message": "Cart deleted successfully",
        "data": {},
        "metadata": {"request_id": getattr(request.state, "request_id", None)},
    }
    return jsonable_encoder(payload)


# Add item to cart
@router.post("/{cart_id}/items", response_model=SuccessResponse[CartItemSchema], responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}, status_code=status.HTTP_201_CREATED)
def add_item(request: Request, cart_id: str, item: CartItemCreateSchema, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        return error_response(message="Cart not found", code=404, metadata={"request_id": getattr(request.state, "request_id", None)})

    if item.quantity <= 0:
        return error_response(message="Quantity must be > 0", code=400, metadata={"request_id": getattr(request.state, "request_id", None)})

    try:
        db_item = CartItemModel(cart_id=cart_id, product_id=str(item.product_id), quantity=int(item.quantity))
        db.add(db_item)
        db.commit()
        db.refresh(db_item)

        item_data = _to_cart_item_dict(db_item)
        payload = {
            "code": 201,
            "status": "success",
            "message": "Item added to cart",
            "data": item_data,
            "metadata": {"request_id": getattr(request.state, "request_id", None)},
        }
        return jsonable_encoder(payload)
    except Exception as e:
        return error_response(message="Failed to add item", code=500, details=str(e), metadata={"request_id": getattr(request.state, "request_id", None)})


# Update item
@router.put("/{cart_id}/items/{item_id}", response_model=SuccessResponse[CartItemSchema], responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_item(request: Request, cart_id: str, item_id: str, item: CartItemUpdateSchema, db: Session = Depends(get_db)):
    db_item = db.query(CartItemModel).filter(CartItemModel.id == item_id, CartItemModel.cart_id == cart_id).first()
    if not db_item:
        return error_response(message="Cart item not found", code=404, metadata={"request_id": getattr(request.state, "request_id", None)})

    if item.quantity is not None:
        if item.quantity <= 0:
            return error_response(message="Quantity must be > 0", code=400, metadata={"request_id": getattr(request.state, "request_id", None)})
        db_item.quantity = int(item.quantity)

    db.commit()
    db.refresh(db_item)

    item_data = _to_cart_item_dict(db_item)
    payload = {
        "code": 200,
        "status": "success",
        "message": "Cart item updated",
        "data": item_data,
        "metadata": {"request_id": getattr(request.state, "request_id", None)},
    }
    return jsonable_encoder(payload)


# Delete item
@router.delete("/{cart_id}/items/{item_id}", response_model=SuccessResponse[dict], responses={404: {"model": ErrorResponse}})
def delete_item(request: Request, cart_id: str, item_id: str, db: Session = Depends(get_db)):
    db_item = db.query(CartItemModel).filter(CartItemModel.id == item_id, CartItemModel.cart_id == cart_id).first()
    if not db_item:
        return error_response(message="Cart item not found", code=404, metadata={"request_id": getattr(request.state, "request_id", None)})
    db.delete(db_item)
    db.commit()

    payload = {
        "code": 200,
        "status": "success",
        "message": "Item removed successfully",
        "data": {},
        "metadata": {"request_id": getattr(request.state, "request_id", None)},
    }
    return jsonable_encoder(payload)
