import os
from urllib.parse import quote_plus

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Получаем логин и пароль из .env, экранируем их
username = quote_plus(os.getenv("mongo_username"))
password = quote_plus(os.getenv("mongo_password"))

host = "77.232.135.48"
port = "27017"

# Формируем безопасный URI
mongo_uri = f"mongodb://{username}:{password}@{host}:{port}"

try:
    client = MongoClient(mongo_uri)
    client.server_info()  # Проверка подключения
    print("✅ Подключение к MongoDB установлено")
except Exception as e:
    print(f"⚠️ Ошибка подключения к MongoDB: {e}")
    raise

# Используем БД
db = client["users"]
