# routes/hub.py
from fastapi import APIRouter, HTTPException

import config
from database import db
from services.hub_service import search_products, index_offer, index_trust, load_hubs

router = APIRouter(prefix="/hub", tags=["hub"], include_in_schema=False)

def check_enabled():
    if not config.HUB_MODE:
        raise HTTPException(status_code=404)

@router.post("/inbox")
async def hub_inbox(activity: dict):
    check_enabled()
    atype = activity.get("type")
    if atype == "Offer":
        await index_offer(activity)
    elif atype == "fedmarket:Trust":
        await index_trust(activity)
    return {"status": "indexed"}

@router.get("/search")
async def search(q: str = None, tag: str = "", min_price: float = None, max_price: float = None, limit: int = 20):
    check_enabled()
    results = await search_products(q, tag, min_price, max_price, limit)
    return {"results": results}

@router.get("/hubs")
async def list_hubs():
    check_enabled()
    return load_hubs()

@router.get("/info")
async def info():
    check_enabled()
    return {
        "name": config.HUB_NAME,
        "domain": config.HUB_DOMAIN,
        "mode": "hub",
        "offers": await db.hub_offers.count_documents({}),
        "trust_links": await db.hub_trust_log.count_documents({})
    }
