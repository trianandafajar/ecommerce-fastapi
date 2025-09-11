# app/routers/cart.py
import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder

from app.utils.database import SessionLocal
from app.utils.auth import get_current_user_optional, get_current_user
from app.models.cart import Cart as CartModel, CartItem as CartItemModel
from app.models.user import User
from app.schemas.cart import (
    Cart as CartSchema,
    CartCreate as CartCreateSchema,
    CartItem as CartItemSchema,
    CartItemCreate as CartItemCreateSchema,
    CartItemUpdate as CartItemUpdateSchema,
)
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response

API_URL = "/carts"
router = APIRouter(prefix=API_URL, tags=["Carts"])


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helpers
def _to_cart_dict(cart_orm: CartModel) -> dict:
    return CartSchema.model_validate(cart_orm).model_dump()


def _to_cart_item_dict(item_orm: CartItemModel) -> dict:
    return CartItemSchema.model_validate(item_orm).model_dump()


# ---------------- CART ROUTES ----------------

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
    """Get list of carts"""
    try:
        carts_db = db.query(CartModel).offset(skip).limit(limit).all()
        carts = [_to_cart_dict(c) for c in carts_db]

        metadata = {
            "request_id": getattr(request.state, "request_id", None),
            "pagination": {
                "page": (skip // limit) + 1 if limit else 1,
                "per_page": limit,
                "total": len(carts),
            },
        }

        return success_response(
            message="Carts fetched",
            data=carts,
            metadata=metadata
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch carts",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


@router.get(
    "/lookup",
    response_model=SuccessResponse[CartSchema],
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
def read_cart_lookup(
    request: Request,
    session_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),  # optional auth
):
    """
    Lookup cart:
    - If authenticated: use current_user.id
      - If cart not exists -> create a new cart tied to the user and return it
    - Else (guest): require session_id and return the cart for that session (404 if not found)
    """
    if not current_user and not session_id:
        return error_response(
            message="Either authenticated user or session_id is required",
            code=400,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    query = db.query(CartModel).options(
        joinedload(CartModel.items).joinedload(CartItemModel.product)
    )

    cart = None

    if current_user:
        cart = query.filter(CartModel.user_id == str(current_user.id)).first()
        if not cart:
            cart = CartModel(user_id=str(current_user.id), session_token=None)
            db.add(cart)
            db.commit()

            db.refresh(cart)
            cart = db.query(CartModel).options(
                joinedload(CartModel.items).joinedload(CartItemModel.product)
            ).filter(CartModel.id == cart.id).first()
    else:
        cart = query.filter(CartModel.session_token == session_id).first()
        if not cart:
            return error_response(
                message="Cart not found",
                code=404,
                metadata={"request_id": getattr(request.state, "request_id", None)},
            )

    return success_response(
        message="Cart fetched",
        data=_to_cart_dict(cart),
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )

@router.post(
    "/",
    response_model=SuccessResponse[CartSchema],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
def create_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ⬅️ user harus login
):
    """Create cart (only allowed for authenticated users)"""
    try:
        existing_cart = db.query(CartModel).filter(
            CartModel.user_id == str(current_user.id)
        ).first()
        if existing_cart:
            return error_response(
                message="User already has a cart",
                code=400,
                metadata={"request_id": getattr(request.state, "request_id", None)},
            )

        db_cart = CartModel(
            user_id=str(current_user.id),
            session_token=None,
        )
        db.add(db_cart)
        db.commit()
        db.refresh(db_cart)

        return success_response(
            message="Cart created",
            data=_to_cart_dict(db_cart),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to create cart",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )



@router.get(
    "/{cart_id}",
    response_model=SuccessResponse[CartSchema],
    responses={404: {"model": ErrorResponse}},
)
def read_cart(request: Request, cart_id: str, db: Session = Depends(get_db)):
    """Get cart detail by ID"""
    cart = db.query(CartModel).options(
        joinedload(CartModel.items).joinedload(CartItemModel.product)
    ).filter(CartModel.id == cart_id).first()
    if not cart:
        return error_response(
            message="Cart not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    return success_response(
        message="Cart fetched",
        data=_to_cart_dict(cart),
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.delete(
    "/{cart_id}",
    response_model=SuccessResponse[dict],
    responses={404: {"model": ErrorResponse}},
)
def delete_cart(request: Request, cart_id: str, db: Session = Depends(get_db)):
    """Delete cart"""
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        return error_response(
            message="Cart not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    db.delete(cart)
    db.commit()

    return success_response(
        message="Cart deleted successfully",
        data={},
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


# ---------------- CART ITEMS ----------------

@router.post(
    "/{cart_id}/items",
    response_model=SuccessResponse[CartItemSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
def add_item(request: Request, cart_id: str, item: CartItemCreateSchema, db: Session = Depends(get_db)):
    """Add item to cart"""
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        return error_response(message="Cart not found", code=404)

    if item.quantity <= 0:
        return error_response(message="Quantity must be > 0", code=400)

    try:
        db_item = CartItemModel(
            cart_id=cart_id,
            product_id=str(item.product_id),
            quantity=int(item.quantity),
        )
        db.add(db_item)
        db.commit()
        # refresh and re-query to include product relation
        db.refresh(db_item)
        db_item = db.query(CartItemModel).options(joinedload(CartItemModel.product)).filter(CartItemModel.id == db_item.id).first()

        return success_response(
            message="Item added to cart",
            data=_to_cart_item_dict(db_item),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(message="Failed to add item", code=500, details=str(e))


@router.put(
    "/{cart_id}/items/{item_id}",
    response_model=SuccessResponse[CartItemSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def update_item(request: Request, cart_id: str, item_id: str, item: CartItemUpdateSchema, db: Session = Depends(get_db)):
    """Update item in cart"""
    db_item = db.query(CartItemModel).filter(
        CartItemModel.id == item_id, CartItemModel.cart_id == cart_id
    ).first()
    if not db_item:
        return error_response(message="Cart item not found", code=404)

    if item.quantity is not None:
        if item.quantity <= 0:
            return error_response(message="Quantity must be > 0", code=400)
        db_item.quantity = int(item.quantity)

    db.commit()
    db.refresh(db_item)
    db_item = db.query(CartItemModel).options(joinedload(CartItemModel.product)).filter(CartItemModel.id == db_item.id).first()

    return success_response(
        message="Cart item updated",
        data=_to_cart_item_dict(db_item),
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


@router.delete(
    "/{cart_id}/items/{item_id}",
    response_model=SuccessResponse[dict],
    responses={404: {"model": ErrorResponse}},
)
def delete_item(request: Request, cart_id: str, item_id: str, db: Session = Depends(get_db)):
    """Delete item from cart"""
    db_item = db.query(CartItemModel).filter(
        CartItemModel.id == item_id, CartItemModel.cart_id == cart_id
    ).first()
    if not db_item:
        return error_response(message="Cart item not found", code=404)

    db.delete(db_item)
    db.commit()

    return success_response(
        message="Item removed successfully",
        data={},
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )
