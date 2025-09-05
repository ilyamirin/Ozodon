# main.py
import config as config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from services.hub_service import replicate_to_peers
from routes.hub import router as hub_router
from routes.web import router as web_router

app = FastAPI(title="Ozodon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# БД
client = AsyncIOMotorClient(config.MONGODB_URI)
db = client[config.DATABASE_NAME]

# Подключение контроллеров (роутеров) и статики
if config.HUB_MODE:
    # Роуты хаба и веб-страницы
    app.include_router(hub_router)
    app.mount("/static", __import__("fastapi.staticfiles").staticfiles.StaticFiles(directory="static"), name="static")
    app.include_router(web_router)

@app.on_event("startup")
async def startup():
    from database import ping_db
    await ping_db()
    if config.HUB_MODE:
        print(f"🌍 Хаб включён: {config.HUB_DOMAIN}")

@app.post("/inbox")
async def inbox(activity: dict):
    atype = activity.get("type")

    if atype == "Offer" and config.HUB_MODE:
        from services.hub_service import index_offer
        await index_offer(activity)
        await replicate_to_peers(activity)

    elif atype == "fedmarket:Trust" and config.HUB_MODE:
        from services.hub_service import index_trust
        await index_trust(activity)
        await replicate_to_peers(activity)

    return {"status": "received"}
