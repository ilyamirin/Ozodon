"""Hub-related FastAPI routes.

These endpoints are available only when HUB_MODE is enabled. The router exposes
inbox processing, search, simple trust scoring, tag/category stats, and basic
hub info suited for lightweight federation scenarios.
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

import config
from database import db
from services.hub_service import index_offer, index_trust, load_hubs, search_products

router = APIRouter(prefix="/hub", tags=["hub"], include_in_schema=False)


def check_enabled() -> None:
    """Guard endpoint access when HUB_MODE is disabled.

    Raises:
        HTTPException: 404 to mimic absence of hub endpoints entirely.
    """
    if not config.HUB_MODE:
        raise HTTPException(status_code=404)


@router.post("/inbox")
async def hub_inbox(activity: dict) -> dict:
    """Index incoming activities relevant to the hub (Offer/Trust)."""
    check_enabled()
    atype = activity.get("type")
    if atype == "Offer":
        await index_offer(activity)
    elif atype == "fedmarket:Trust":
        await index_trust(activity)
    return {"status": "indexed"}


@router.get("/search")
async def search(
    q: str | None = None,
    tag: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
) -> dict:
    """Search products indexed by the hub with optional filters."""
    check_enabled()
    results = await search_products(q, tag, min_price, max_price, limit)
    return {"results": results}


@router.get("/trust/score")
async def trust_score(actor: str) -> Dict[str, Any]:
    """Простейший расчёт репутации на основе входящих связей доверия.

    Если входящих нет — возвращаем 0.5 как нейтральный балл.
    """
    check_enabled()
    pipeline = [
        {"$match": {"target": actor}},
        {"$group": {"_id": "$target", "avg_weight": {"$avg": "$weight"}, "count": {"$sum": 1}}},
    ]
    agg = await db.hub_trust_log.aggregate(pipeline).to_list(length=1)
    if agg:
        score = float(agg[0].get("avg_weight", 0.5))
        count = int(agg[0].get("count", 0))
    else:
        score, count = 0.5, 0
    return {"actor": actor, "score": score, "votes": count}


@router.get("/hubs")
async def list_hubs() -> list[dict]:
    """Return the static registry of hubs to replicate to."""
    check_enabled()
    return load_hubs()


@router.get("/seller/{actor_id}")
async def seller(actor_id: str) -> dict:
    """Return seller's offers and a simple trust score summary."""
    check_enabled()
    offers = (
        await db.hub_offers.find({"seller": actor_id}).sort("published", -1).limit(100).to_list(length=100)
    )
    # Получим базовый скор (перевызов обработчика безопасен)
    score_doc = await trust_score(actor_id)
    return {"seller": actor_id, "trust": score_doc, "offers": offers}


@router.get("/feeds/latest")
async def feeds_latest(limit: int = 20) -> dict:
    """Return the latest offers feed."""
    check_enabled()
    cursor = db.hub_offers.find({}).sort("published", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items, "limit": limit}


@router.get("/tags")
async def tags_top(limit: int = 50) -> dict:
    """Return top tags with counts computed via aggregation pipeline."""
    check_enabled()
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    tags = await db.hub_offers.aggregate(pipeline).to_list(length=limit)
    # Приводим к простому виду
    return {"tags": [{"tag": t["_id"], "count": t["count"]} for t in tags]}


@router.get("/categories")
async def categories() -> dict:
    """Return a simplified list of categories based on top tags."""
    check_enabled()
    # Упрощение: категории как верхние теги
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    cats = await db.hub_offers.aggregate(pipeline).to_list(length=20)
    return {"categories": [c["_id"] for c in cats]}


@router.post("/replicate")
async def replicate(activity: dict) -> dict:
    """Приём репликации между хабами — делаем то же, что и в inbox"""
    return await hub_inbox(activity)


@router.get("/info")
async def info() -> dict:
    """Return basic information and counters for the hub."""
    check_enabled()
    return {
        "name": config.HUB_NAME,
        "domain": config.HUB_DOMAIN,
        "mode": "hub",
        "offers": await db.hub_offers.count_documents({}),
        "trust_links": await db.hub_trust_log.count_documents({}),
    }
