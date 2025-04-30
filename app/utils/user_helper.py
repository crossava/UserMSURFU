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
    print("Начало")
    msg = EmailMessage()
    msg["Subject"] = "Код подтверждения регистрации"
    msg["From"] = SMTP_USER
    msg["To"] = recipient_email
    msg.set_content(f"Ваш код подтверждения: {confirmation_code}")

    try:
        print("→ Подключение к SMTP...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            print("→ Старт TLS...")
            server.starttls()
            print("→ Логин...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("→ Отправка письма...")
            server.send_message(msg)
        print(f"✅ Код отправлен на {recipient_email}")
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")


def confirm_email(data: dict, action: str) -> dict:
    email = data.get("email")
    code = data.get("confirmation_code")

    if not email or not code:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Email и код обязательны"
            }
        }

    user = db.users.find_one({"email": email})

    if not user:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Пользователь не найден"
            }
        }

    if user.get("is_email_confirmed"):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Почта уже подтверждена"
            }
        }

    if user.get("confirmation_code") != code:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Неверный код подтверждения"
            }
        }

    db.users.update_one(
        {"email": email},
        {
            "$set": {"is_email_confirmed": True},
            "$unset": {"confirmation_code": ""}
        }
    )

    return {
        "message": {
            "action": action,
            "status": "success",
            "text": "Почта подтверждена"
        }
    }


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
