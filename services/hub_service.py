# services/hub_service.py
import httpx
import json

from database import db
from config import HUBS_FILE
import config

try:
    from services.trust_service import compute_trust_score as _compute_trust_path
except Exception:
    _compute_trust_path = None

# Загружаем реестр хабов
def load_hubs():
    with open(HUBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def index_offer(activity: dict):
    obj = activity.get("object", {})
    offers_data = obj.get("schema:offers", {})
    product = {
        "id": obj.get("id") or activity.get("id"),
        "name": obj.get("schema:name", ""),
        "description": obj.get("schema:description", ""),
        "image": obj.get("schema:image"),
        "price": float(offers_data.get("schema:price", 0)),
        "currency": offers_data.get("schema:priceCurrency", "TON"),
        "seller": activity["actor"],
        "origin_instance": activity["actor"].split("/")[2],
        "tags": [t["name"].lstrip("#") for t in activity.get("tag", [])],
        "published": activity.get("published"),
        "source_activity": activity
    }
    await db.hub_offers.update_one({"id": product["id"]}, {"$set": product}, upsert=True)
    return product

async def index_trust(activity: dict):
    if activity["type"] != "fedmarket:Trust":
        return None
    obj = activity["object"]
    trust = {
        "source": activity["actor"],
        "target": obj["target"],
        "weight": obj["weight"],
        "timestamp": obj.get("issued") or activity.get("published")
    }
    await db.hub_trust_log.update_one(
        {"source": trust["source"], "target": trust["target"]},
        {"$set": trust},
        upsert=True
    )
    return trust

async def _seller_reputation(seller: str) -> float:
    """Compute a reputation score for a seller using trust graph if available.
    Fallback to neutral 0.5 when trust service is unavailable.
    """
    try:
        if _compute_trust_path is None:
            return 0.5
        # Without a designated evaluator, approximate by self-reachability as placeholder
        score = await _compute_trust_path(seller, seller)
        # Bound score into [0,1] and soften extremes
        score = max(0.0, min(1.0, float(score)))
        return 0.5 + (score - 0.5) * 0.8
    except Exception:
        return 0.5

async def search_products(q: str = None, tag: str = None, min_price: float = None, max_price: float = None, limit: int = 20):
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}}
        ]
    if tag:
        query["tags"] = tag.lstrip("#")
    if min_price is not None:
        query["price"] = {"$gte": min_price}
    if max_price is not None:
        query["price"] = {**query.get("price", {}), "$lte": max_price}

    cursor = db.hub_offers.find(query).sort("price", 1).limit(limit)
    products = await cursor.to_list(length=limit)

    # 🔝 Ранжирование по репутации продавца
    for p in products:
        trust_score = await _seller_reputation(p["seller"])
        p["reputation_score"] = trust_score
        p["rank_score"] = p["price"] * (1.5 - trust_score)  # чем выше доверие — тем выше вес

    # Сортируем по rank_score
    products.sort(key=lambda x: x["rank_score"])
    return products

# Репликация
async def replicate_to_peers(activity: dict):
    """Отправляет объект всем активным хабам из реестра"""
    hubs = load_hubs()
    async with httpx.AsyncClient() as client:
        for hub in hubs:
            if hub["active"] and hub["domain"] != config.HUB_DOMAIN:
                try:
                    await client.post(f"{hub['domain']}/hub/inbox", json=activity, timeout=10)
                except Exception as e:
                    print(f"❌ Не удалось реплицировать в {hub['domain']}: {e}")
