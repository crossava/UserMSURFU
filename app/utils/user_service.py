import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from random import randint

from passlib.hash import bcrypt
from app.core.mongo_config import db
from dotenv import load_dotenv
import jwt

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 1


def register_user(data: dict, action: str) -> dict:
    required_fields = {"email", "full_name", "role", "password"}
    if not required_fields.issubset(data):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Отсутствуют обязательные поля"
            }}

    email = data["email"]
    full_name = data["full_name"]
    role = data["role"]
    password = data["password"]

    # Проверка на существующего пользователя
    if db.users.find_one({"email": email}):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Пользователь с таким email уже существует"
            }
        }

    hashed_password = bcrypt.hash(password)

    # Генерация 4-значного кода подтверждения
    confirmation_code = f"{randint(1000, 9999)}"

    user_data = {
        "email": email,
        "full_name": full_name,
        "role": role,
        "hashed_password": hashed_password,
        "is_blocked": False,
        "blocked_until": None,
        "is_email_confirmed": False,
        "confirmation_code": confirmation_code,
        "created_at": datetime.utcnow()
    }

    db.users.insert_one(user_data)

    # Здесь можно вставить отправку письма пользователю
    send_email_confirmation(email, confirmation_code)

    return {
        "message": {
            "action": action,
            "status": "success",
            "text": f"Письмо с кодом подтверждения отправлено на {email}"
        }
    }


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def login_user(data: dict, action: str) -> dict:
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Email и пароль обязательны"
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

    if not user.get("is_email_confirmed"):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Почта не подтверждена"
            }
        }

    if not bcrypt.verify(password, user["hashed_password"]):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Неверный пароль"
            }
        }

    payload = {
        "sub": user["email"],
        "role": user["role"],
        "full_name": user["full_name"],
    }

    access_token = create_token(payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_token(payload, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    return {
        "message": {
            "action": action,
            "status": "success",
            "body": {
                "user_id": str(user["_id"]),
                "full_name": user["full_name"],
                "role": user["role"],
                "email": user["email"],
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        }
    }


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
