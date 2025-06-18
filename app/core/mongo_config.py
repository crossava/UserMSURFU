# app/core/mongo_config.py
from pymongo import MongoClient, ASCENDING
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

# Подключение к MongoDB
username = quote_plus(os.getenv("mongo_username"))
password = quote_plus(os.getenv("mongo_password"))
MONGO_URI = f"mongodb://{username}:{password}@212.113.117.163:27017"
client = MongoClient(MONGO_URI)
db = client["users"]

# Создание уникального индекса для email
db.users.create_index([("email", ASCENDING)], unique=True)