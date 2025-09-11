# app/utils/otp.py
import random, datetime
from sqlalchemy.orm import Session
from app.models.otp import OTP
from app.models import User as UserModel
from app.utils.email import send_email
from app.utils.templates.otp_email import build_otp_email

def generate_otp(db: Session, user_id: str) -> str:
    code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    otp = OTP(user_id=user_id, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return code

def send_otp_email(email: str, code: str, user_name: str = "User"):
    subject = "Your OTP Code"
    html_body = build_otp_email(code=code, user_name=user_name)

    return send_email(
        to_email=email,
        subject=subject,
        html_body=html_body,
    )
