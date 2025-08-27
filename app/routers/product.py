from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.utils.database import SessionLocal
from app.models import Product as ProductModel
from app.schemas import Product, ProductCreate, ProductUpdate


API_URL = '/products'
router = APIRouter(prefix=API_URL, tags=["Products"])

def get_db(): 
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# get all product
@router.get('/', response_model=List[Product])
def read_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    products = db.query(ProductModel).offset(skip).limit(limit).all()
    return products 

# create product
@router.post('/', response_model=Product, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = ProductModel(
        name=product.name,
        description=product.description,
        price=product.price,
        image_url=str(product.image_url)
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# get detail product
@router.get('/{product_id}', response_model=Product)
def read_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# update product
@router.put("/{product_id}", response_model=Product)
def update_product(product_id: str, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in product.dict(exclude_unset=True).items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product

# delete product
@router.delete("/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db)):
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}