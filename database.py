"""Database client initialization for Ozodon.

Exposes a Motor AsyncIOMotorClient and database handle for reuse. Includes a
simple readiness check used during application startup.
"""
from motor.motor_asyncio import AsyncIOMotorClient

from config import DATABASE_NAME, MONGODB_URI

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DATABASE_NAME]


async def ping_db() -> None:
    """Ping the MongoDB server to verify connectivity.

    Prints a human-friendly message to stdout; errors are caught and displayed
    without raising to avoid crashing the app on non-critical startup checks.
    """
    try:
        await client.admin.command("ping")
        print("✅ Подключение к MongoDB успешно")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
