# app/utils/user_helper.py
import os
import smtplib
from datetime import timedelta, datetime
from email.message import EmailMessage
import jwt
from dotenv import load_dotenv
from app.core.mongo_config import db

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 1

def send_email_confirmation(recipient_email: str, confirmation_code: str):
    msg = EmailMessage()
    msg["Subject"] = "Код подтверждения регистрации"
    msg["From"] = SMTP_USER
    msg["To"] = recipient_email
    msg.set_content(f"Ваш код подтверждения: {confirmation_code}")
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"✅ Код отправлен на {recipient_email}")
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")

def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)