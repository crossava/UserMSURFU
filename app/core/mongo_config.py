from urllib.parse import quote_plus
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

username = quote_plus(os.getenv("mongo_username"))
password = quote_plus(os.getenv("mongo_password"))

MONGO_URI = f"mongodb://{username}:{password}@77.232.135.48:27017"
client = MongoClient(MONGO_URI)
db = client["users"]
