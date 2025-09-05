# database.py
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, DATABASE_NAME

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DATABASE_NAME]

async def ping_db():
    try:
        await client.admin.command('ping')
        print("✅ Подключение к MongoDB успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения к MongoDB: {e}")
