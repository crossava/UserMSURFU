# app/services/user_service.py
from datetime import datetime, timedelta
from random import randint
import re
import jwt
from passlib.hash import bcrypt
from app.core.mongo_config import db
from dotenv import load_dotenv
from app.utils.user_helper import (
    create_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
    send_email_confirmation, JWT_SECRET, JWT_ALGORITHM
)

# Валидация email
def validate_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]

def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+7\d{10}$", phone))

def get_all_users(action: str):
    try:
        users_cursor = db.users.find()
        users = []
        for user in users_cursor:
            user["_id"] = str(user["_id"])
            user.pop("hashed_password", None)
            # Преобразование datetime в ISO-формат
            for field in ["created_at", "updated_at", "last_login"]:
                if field in user and isinstance(user[field], datetime):
                    user[field] = user[field].isoformat()
            users.append(user)
        return {
            "action": action,
            "message": {
                "status": "success",
                "users": users
            }
        }
    except Exception as e:
        return {
            "action": action,
            "message": {
                "status": "error",
                "details": str(e)
            }
        }

def register_user(data: dict, action: str) -> dict:
    required_fields = {"email", "full_name", "role", "password", "phone"}
    if not required_fields.issubset(data):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Отсутствуют обязательные поля"
            }
        }

    email = data["email"].lower().strip()
    full_name = data["full_name"].strip()
    role = data["role"].strip().lower()
    password = data["password"]
    phone = data.get("phone")  # Опциональное поле

    if not validate_email(email):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Некорректный формат email"
            }
        }

    if phone and not validate_phone(phone):
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Неверный формат телефона"
            }
        }

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
    confirmation_code = f"{randint(100000, 999999)}"  # 6-значный код

    user_data = {
        "email": email,
        "full_name": full_name,
        "role": role,
        "hashed_password": hashed_password,
        "phone": phone,  # Добавляем телефон
        "is_blocked": False,
        "blocked_until": None,
        "is_email_confirmed": False,
        "confirmation_code": confirmation_code,
        "created_at": datetime.utcnow()
    }

    try:
        db.users.insert_one(user_data)
        send_email_confirmation(email, confirmation_code)
        return {
            "message": {
                "action": action,
                "status": "success",
                "text": f"Письмо с кодом подтверждения отправлено на {email}"
            }
        }
    except Exception as e:
        print(f"⚠️ Ошибка регистрации: {str(e)}")
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Внутренняя ошибка сервера"
            }
        }

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
                "phone": user.get("phone"),  # Возвращаем телефон
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        }
    }