"""Ozodon FastAPI application entrypoint.

This module wires the web application, configures CORS, initializes MongoDB,
mounts routers, and exposes ActivityPub-compatible and helper endpoints.

All route handlers include docstrings for clarity and to comply with strict
Python documentation standards.
"""
import config as config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from routes.hub import router as hub_router
from routes.web import router as web_router
from services.hub_service import replicate_to_peers

app = FastAPI(title="Ozodon")

# Configure permissive CORS for demo purposes. In production, restrict origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database client for global access within this module
client = AsyncIOMotorClient(config.MONGODB_URI)
db = client[config.DATABASE_NAME]

# Mount hub-specific routers and static files when the app runs in HUB_MODE.
if config.HUB_MODE:
    app.include_router(hub_router)
    app.mount(
        "/static",
        __import__("fastapi.staticfiles").staticfiles.StaticFiles(directory="static"),
        name="static",
    )
    app.include_router(web_router)


@app.on_event("startup")
async def startup() -> None:
    """Perform startup checks and log hub status if applicable."""
    from database import ping_db

    await ping_db()
    if config.HUB_MODE:
        print(f"🌍 Хаб включён: {config.HUB_DOMAIN}")


# --- ActivityPub generic inbox ---
@app.post("/inbox")
async def inbox(activity: dict) -> dict:
    """Accept arbitrary ActivityPub activities and index relevant ones.

    For Offer and fedmarket:Trust activities in HUB_MODE, index locally and
    replicate to known peers.
    """
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
async def user_profile(username: str) -> dict:
    """Return a minimal ActivityPub Person object for a username."""
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
        "url": actor_id,
    }


@app.post("/users/{username}/inbox")
async def user_inbox(username: str, activity: dict) -> dict:
    """Delegate per-user inbox to the generic inbox for indexing."""
    return await inbox(activity)


@app.get("/users/{username}/outbox")
async def user_outbox(username: str) -> dict:
    """Return an empty outbox placeholder for compatibility."""
    return {
        "@context": ["https://www.w3.org/ns/activitystreams"],
        "type": "OrderedCollection",
        "totalItems": 0,
        "orderedItems": [],
    }


@app.get("/users/{username}/followers")
async def user_followers(username: str) -> dict:
    """Return an empty followers collection placeholder."""
    return {"type": "OrderedCollection", "totalItems": 0, "orderedItems": []}


@app.get("/users/{username}/following")
async def user_following(username: str) -> dict:
    """Return an empty following collection placeholder."""
    return {"type": "OrderedCollection", "totalItems": 0, "orderedItems": []}


# --- WebFinger ---
@app.get("/.well-known/webfinger")
async def webfinger(resource: str) -> JSONResponse:
    """Serve a simple WebFinger endpoint for local users.

    Args:
        resource: Expected to be in the form "acct:username@domain".
    """
    if not resource.startswith("acct:"):
        raise HTTPException(status_code=400, detail="Unsupported resource")
    try:
        acct = resource.split(":", 1)[1]
        username, domain = acct.split("@", 1)
    except Exception:  # invalid input shape
        raise HTTPException(status_code=400, detail="Invalid acct")

    # Only answer for our domain; otherwise return 404
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
async def nodeinfo_index() -> dict:
    """Return NodeInfo index pointing at the 2.0 schema."""
    return {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": f"{config.HUB_DOMAIN}/nodeinfo/2.0",
            }
        ]
    }


@app.get("/nodeinfo/2.0")
async def nodeinfo() -> dict:
    """Return a minimal NodeInfo 2.0 payload with hub metadata."""
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
async def timeline_public(limit: int = 20) -> dict:
    """Return a simple public timeline of latest offers."""
    cursor = db.hub_offers.find({}).sort("published", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items, "limit": limit}


# --- Simple API ---
@app.get("/api/v1/products")
async def api_products(
    q: str | None = None,
    tag: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
) -> dict:
    """Search products via the service layer and return results.

    Args:
        q: Full-text search term across name and description.
        tag: Optional tag to filter by (with or without '#').
        min_price: Minimum price filter.
        max_price: Maximum price filter.
        limit: Maximum number of items to return.
    """
    from services.hub_service import search_products

    results = await search_products(q, tag, min_price, max_price, limit)
    return {"results": results}
