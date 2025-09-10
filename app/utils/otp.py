# app/utils/otp.py
import random, datetime
from sqlalchemy.orm import Session
from app.models.otp import OTP
from app.models import User as UserModel

def generate_otp(db: Session, user_id: str) -> str:
    code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    otp = OTP(user_id=user_id, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return code

def send_otp_email(email: str, code: str):
    # 🚨 Integrasi ke provider email (misal SendGrid, SMTP, Mailgun)
    print(f"[DEBUG] Kirim OTP {code} ke email {email}")
