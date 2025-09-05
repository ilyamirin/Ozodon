# main.py
import config as config
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# --- ActivityPub generic inbox ---
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

# --- ActivityPub user stubs ---
@app.get("/users/{username}")
async def user_profile(username: str):
    actor_id = f"{config.HUB_DOMAIN}/users/{username}"
    return {
        "@context": ["https://www.w3.org/ns/activitystreams"],
        "id": actor_id,
        "type": "Person",
        "preferredUsername": username,
        "inbox": f"{actor_id}/inbox",
        "outbox": f"{actor_id}/outbox",
        "followers": f"{actor_id}/followers",
        "following": f"{actor_id}/following",
        "url": actor_id
    }

@app.post("/users/{username}/inbox")
async def user_inbox(username: str, activity: dict):
    # Делегируем в общий inbox для индексации Offer/Trust
    return await inbox(activity)

@app.get("/users/{username}/outbox")
async def user_outbox(username: str):
    return {
        "@context": ["https://www.w3.org/ns/activitystreams"],
        "type": "OrderedCollection",
        "totalItems": 0,
        "orderedItems": []
    }

@app.get("/users/{username}/followers")
async def user_followers(username: str):
    return {"type": "OrderedCollection", "totalItems": 0, "orderedItems": []}

@app.get("/users/{username}/following")
async def user_following(username: str):
    return {"type": "OrderedCollection", "totalItems": 0, "orderedItems": []}

# --- WebFinger ---
@app.get("/.well-known/webfinger")
async def webfinger(resource: str):
    # Expect resource like: acct:username@domain
    if not resource.startswith("acct:"):
        raise HTTPException(status_code=400, detail="Unsupported resource")
    try:
        acct = resource.split(":", 1)[1]
        username, domain = acct.split("@", 1)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid acct")
    # Only answer for our domain, otherwise minimal 404
    hub_domain = config.HUB_DOMAIN.replace("https://", "").replace("http://", "")
    if domain != hub_domain:
        raise HTTPException(status_code=404)
    subject = f"acct:{username}@{domain}"
    actor = f"{config.HUB_DOMAIN}/users/{username}"
    return JSONResponse(
        {
            "subject": subject,
            "links": [
                {"rel": "self", "type": "application/activity+json", "href": actor},
            ],
        },
        media_type="application/jrd+json",
    )

# --- NodeInfo ---
@app.get("/.well-known/nodeinfo")
async def nodeinfo_index():
    return {
        "links": [
            {"rel": "http://nodeinfo.diaspora.software/ns/schema/2.0", "href": f"{config.HUB_DOMAIN}/nodeinfo/2.0"}
        ]
    }

@app.get("/nodeinfo/2.0")
async def nodeinfo():
    offers = await db.hub_offers.count_documents({}) if config.HUB_MODE else 0
    trust_links = await db.hub_trust_log.count_documents({}) if config.HUB_MODE else 0
    return {
        "version": "2.0",
        "software": {"name": "ozodon", "version": "0.1"},
        "protocols": ["activitypub"],
        "services": {"inbound": [], "outbound": []},
        "openRegistrations": False,
        "usage": {
            "users": {"total": 1},
            "localPosts": offers,
        },
        "metadata": {
            "hub": {
                "name": config.HUB_NAME,
                "domain": config.HUB_DOMAIN,
                "description": config.HUB_DESCRIPTION,
                "offers": offers,
                "trust_links": trust_links,
            }
        },
    }

# --- Public timeline (latest offers) ---
@app.get("/timeline/public")
async def timeline_public(limit: int = 20):
    cursor = db.hub_offers.find({}).sort("published", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items, "limit": limit}

# --- Simple API ---
@app.get("/api/v1/products")
async def api_products(q: str | None = None, tag: str = "", min_price: float | None = None, max_price: float | None = None, limit: int = 20):
    from services.hub_service import search_products
    results = await search_products(q, tag, min_price, max_price, limit)
    return {"results": results}
