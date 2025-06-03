from datetime import datetime, timedelta
from random import randint

import jwt
from passlib.hash import bcrypt
from app.core.mongo_config import db
from dotenv import load_dotenv

from app.utils.user_helper import create_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, \
    send_email_confirmation, JWT_SECRET, JWT_ALGORITHM


def get_all_users(action: str):
    try:
        users_cursor = db.users.find()
        users = []

        for user in users_cursor:
            user["_id"] = str(user["_id"])
            user.pop("password", None)

            # Обработка всех datetime полей
            for field in ["created_at", "updated_at", "last_login"]:  # или любые другие поля
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


def refresh_token_handler(message: dict, action: str) -> dict:
    refresh_token = message.get("refresh_token")
    if not refresh_token:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Refresh token отсутствует"
            }
        }

    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Токен истёк"
            }
        }
    except jwt.InvalidTokenError:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Невалидный токен"
            }
        }

    user = db.users.find_one({"email": payload["sub"]})
    if not user:
        return {
            "message": {
                "action": action,
                "status": "error",
                "text": "Пользователь не найден"
            }
        }

    new_payload = {
        "sub": user["email"],
        "role": user["role"],
        "full_name": user["full_name"],
    }

    access_token = create_token(new_payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_token(new_payload, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    return {
        "message": {
            "action": action,
            "status": "success",
            "body": {
                "access_token": access_token,
                "refresh_token": refresh_token
            }
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
