import os

import stripe


def get_stripe_client():
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    stripe.api_key = secret_key
    return stripe


def get_frontend_url(path: str = "") -> str:
    base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    normalized_path = path if path.startswith("/") or not path else f"/{path}"
    return f"{base_url}{normalized_path}"

