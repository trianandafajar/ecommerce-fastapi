from fastapi import FastAPI
from app.routers import product, auth, cart

app = FastAPI(title="E-Commerce API")

app.include_router(auth.router)
app.include_router(product.router)
app.include_router(cart.router)

@app.get("/")
def root():
    return {"message": "FastAPI E-COMMERCE started sucessfully nih 🚀"}
