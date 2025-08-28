# app/routers/product.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from typing import List
from fastapi.encoders import jsonable_encoder

from app.utils.database import SessionLocal
from app.models import Product as ProductModel
from app.schemas import Product, ProductCreate, ProductUpdate
from app.schemas.response import SuccessResponse, ErrorResponse
from app.utils.response import success_response, error_response

API_URL = "/products"
router = APIRouter(prefix=API_URL, tags=["Products"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Get all products
@router.get(
    "/",
    response_model=SuccessResponse[List[Product]],
    responses={500: {"model": ErrorResponse}},
)
def read_products(
    request: Request, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    try:
        products = db.query(ProductModel).offset(skip).limit(limit).all()
        return success_response(
            data=[Product.model_validate(p).model_dump() for p in products],
            message="Products fetched successfully",
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to fetch products",
            code=500,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


# Create product
@router.post(
    "/",
    response_model=SuccessResponse[Product],
    responses={400: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
)
def create_product(request: Request, product: ProductCreate, db: Session = Depends(get_db)):
    try:
        db_product = ProductModel(
            name=product.name,
            description=product.description,
            price=product.price,
            image_url=str(product.image_url),
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        return success_response(
            data=Product.model_validate(db_product).model_dump(),
            message="Product created successfully",
            code=201,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )
    except Exception as e:
        return error_response(
            message="Failed to create product",
            code=400,
            details=str(e),
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )


# Get detail product
@router.get(
    "/{product_id}",
    response_model=SuccessResponse[Product],
    responses={404: {"model": ErrorResponse}},
)
def read_product(product_id: str, request: Request, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        return error_response(
            message="Product not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    return success_response(
        data=Product.model_validate(product).model_dump(),
        message="Product fetched successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


# Update product
@router.put(
    "/{product_id}",
    response_model=SuccessResponse[Product],
    responses={404: {"model": ErrorResponse}},
)
def update_product(
    product_id: str, product: ProductUpdate, request: Request, db: Session = Depends(get_db)
):
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not db_product:
        return error_response(
            message="Product not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)

    return success_response(
        data=Product.model_validate(db_product).model_dump(),
        message="Product updated successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )


# Delete product
@router.delete(
    "/{product_id}",
    response_model=SuccessResponse[dict],
    responses={404: {"model": ErrorResponse}},
)
def delete_product(product_id: str, request: Request, db: Session = Depends(get_db)):
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not db_product:
        return error_response(
            message="Product not found",
            code=404,
            metadata={"request_id": getattr(request.state, "request_id", None)},
        )

    db.delete(db_product)
    db.commit()

    return success_response(
        data={"deleted_id": product_id},
        message="Product deleted successfully",
        metadata={"request_id": getattr(request.state, "request_id", None)},
    )
