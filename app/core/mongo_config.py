from pymongo import MongoClient

MONGO_URI = "mongodb://jamik:e228Q$_Flb7@77.232.135.48:27017"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Проверяем соединение
    print("✅ Подключение к MongoDB установлено")
except Exception as e:
    print(f"⚠️ Ошибка подключения к MongoDB: {e}")

db = client["users"]


