from fastapi import FastAPI
from app.routers import product

app = FastAPI(title="E-Commerce API")

app.include_router(product.router)

@app.get("/")
def root():
    return {"message": "Hello Reno, FastAPI jalan nih 🚀"}
