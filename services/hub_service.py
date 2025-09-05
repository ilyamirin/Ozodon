"""Hub service helpers: indexing, search, trust handling, replication.

This module implements the core logic for:
- loading the static hubs registry,
- indexing Offer and Trust activities into MongoDB,
- computing a simplified seller reputation for ranking,
- searching products with filters and ranking,
- replicating accepted activities to peer hubs.

The implementation tries to avoid hard failures and prefers safe fallbacks to
keep the hub operating even when optional components are unavailable.
"""
import json
from typing import Any, Dict, List

import httpx

import config
from config import HUBS_FILE
from database import db

try:
    # Optional import: trust service may be absent in some deployments
    from services.trust_service import compute_trust_score as _compute_trust_path
except Exception:  # noqa: BLE001 - intentionally broad to keep service running
    _compute_trust_path = None


def load_hubs() -> List[Dict[str, Any]]:
    """Load the registry of hubs from a JSON file.

    Returns:
        A list of hub descriptors. Each hub may contain fields like domain and
        active. The format is controlled by hubs.json.
    """
    with open(HUBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def index_offer(activity: dict) -> Dict[str, Any]:
    """Index an Offer activity into the hub_offers collection.

    Extracts and normalizes the product fields required for search and display.
    Uses upsert to keep the index idempotent when re-processing the same offer.
    """
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
        # Derive origin instance from actor URL (scheme://host/..)
        "origin_instance": activity["actor"].split("/")[2],
        "tags": [t["name"].lstrip("#") for t in activity.get("tag", [])],
        "published": activity.get("published"),
        # Keep original activity for traceability/debugging
        "source_activity": activity,
    }
    await db.hub_offers.update_one({"id": product["id"]}, {"$set": product}, upsert=True)
    return product


async def index_trust(activity: dict) -> Dict[str, Any] | None:
    """Index a fedmarket:Trust activity into the hub_trust_log collection.

    Returns:
        The normalized trust document, or None if activity type is not Trust.
    """
    if activity.get("type") != "fedmarket:Trust":
        return None
    obj = activity["object"]
    trust = {
        "source": activity["actor"],
        "target": obj["target"],
        "weight": obj["weight"],
        "timestamp": obj.get("issued") or activity.get("published"),
    }
    await db.hub_trust_log.update_one(
        {"source": trust["source"], "target": trust["target"]},
        {"$set": trust},
        upsert=True,
    )
    return trust


async def _seller_reputation(seller: str) -> float:
    """Compute a reputation score for a seller using the trust graph if present.

    Fallback to a neutral 0.5 when the trust service is unavailable or errors
    occur. The returned value is constrained to [0.0, 1.0].
    """
    try:
        if _compute_trust_path is None:
            return 0.5
        # Without a designated evaluator, approximate by self-reachability
        score = await _compute_trust_path(seller, seller)
        # Bound score into [0,1] and soften extremes
        score = max(0.0, min(1.0, float(score)))
        return 0.5 + (score - 0.5) * 0.8
    except Exception:
        return 0.5


async def search_products(
    q: str | None = None,
    tag: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Search products with optional text, tag, and price filters.

    Applies a simple ranking that incorporates price and seller reputation so
    that higher trust can offset price slightly in ordering.
    """
    query: Dict[str, Any] = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if tag:
        query["tags"] = tag.lstrip("#")
    if min_price is not None:
        query["price"] = {"$gte": min_price}
    if max_price is not None:
        query["price"] = {**query.get("price", {}), "$lte": max_price}

    cursor = db.hub_offers.find(query).sort("price", 1).limit(limit)
    products = await cursor.to_list(length=limit)

    # Rank by a blended metric of price and seller reputation
    for p in products:
        trust_score = await _seller_reputation(p["seller"])
        p["reputation_score"] = trust_score
        # The higher the trust, the lower the rank_score multiplier -> better rank
        p["rank_score"] = p["price"] * (1.5 - trust_score)

    products.sort(key=lambda x: x["rank_score"])  # ascending -> best first
    return products


async def replicate_to_peers(activity: dict) -> None:
    """Replicate an accepted activity to all active hubs from the registry.

    Errors during delivery are logged but do not stop the replication loop.
    """
    hubs = load_hubs()
    async with httpx.AsyncClient() as client:
        for hub in hubs:
            if hub.get("active") and hub.get("domain") != config.HUB_DOMAIN:
                try:
                    await client.post(f"{hub['domain']}/hub/inbox", json=activity, timeout=10)
                except Exception as e:  # noqa: BLE001 - keep replication resilient
                    print(f"❌ Не удалось реплицировать в {hub['domain']}: {e}")
