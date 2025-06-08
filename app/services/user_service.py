# app/services/user_service.py
from datetime import datetime, timedelta
from random import randint
import re
import jwt
from bson import ObjectId
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
            for field in ["created_at", "updated_at", "last_login"]:
                if field in user and isinstance(user[field], datetime):
                    user[field] = user[field].isoformat()
            users.append(user)
        return {
            "action": action,
            "status": "success",
            "message": {
                "users": users
            }
        }
    except Exception as e:
        return {
            "action": action,
            "status": "error",
            "message": {
                "details": str(e)
            }
        }


def register_user(data: dict, action: str) -> dict:
    required_fields = {"email", "full_name", "role", "password", "phone", "address"}
    print(data)
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
    phone = data.get("phone")
    address = data.get("address")

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
    confirmation_code = f"{randint(1000, 9999)}"

    user_data = {
        "email": email,
        "full_name": full_name,
        "role": role,
        "hashed_password": hashed_password,
        "phone": phone,
        "address": address,
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
        "phone": user.get("phone"),
        "address": user.get("address"),
        "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
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
                "phone": user.get("phone"),
                "address": user.get("address"),
                "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        }
    }


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


def update_user(data: dict, action: str) -> dict:
    user_id = data.get("user_id")
    if not user_id:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Не передан user_id"
            }
        }

    update_fields = {}
    for field in ["full_name", "phone", "address", "role", "is_blocked", "blocked_until"]:
        if field in data:
            update_fields[field] = data[field]

    if not update_fields:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Нет полей для обновления"
            }
        }

    result = db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

    if result.matched_count == 0:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Пользователь не найден"
            }
        }

    updated_user = db.users.find_one({"_id": ObjectId(user_id)})
    if not updated_user:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Ошибка при получении обновлённого пользователя"
            }
        }

    # Преобразуем ObjectId и datetime для сериализации
    updated_user["_id"] = str(updated_user["_id"])
    if updated_user.get("created_at"):
        updated_user["created_at"] = updated_user["created_at"].isoformat()
    if updated_user.get("blocked_until"):
        updated_user["blocked_until"] = updated_user["blocked_until"].isoformat()

    return {
        "message": {
            "action": action,
            "status": "success",
            "text": "Данные пользователя успешно обновлены",
            "updated_user": updated_user
        }
    }
