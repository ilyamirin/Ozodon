"""Hub-related FastAPI routes.

These endpoints are available only when HUB_MODE is enabled. The router exposes
inbox processing, search, simple trust scoring, tag/category stats, and basic
hub info suited for lightweight federation scenarios.
"""
from typing import Any, Dict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

import config
from database import db
from services.hub_service import index_offer, index_trust, load_hubs, search_products
from services.ton_payment import TONPaymentService, confirm_delivery, request_refund

router = APIRouter(prefix="/hub", tags=["hub"], include_in_schema=False)

# Reuse a single service instance
_payment_service = TONPaymentService()


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


# ---------------------- Payments & Escrow API ----------------------
@router.post("/payments/escrow")
async def create_escrow(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Создать сделку с блокировкой средств (эскроу) и зарезервировать товар.

    Тело запроса:
      - product_id: str — идентификатор товара (Offer.id)
      - buyer_address: str — TON-адрес покупателя
      - amount_ton: float — сумма в TON (как в оффере)
      - timeout_days: int (опц.) — окно для эскроу, по умолчанию 7
    """
    check_enabled()

    product_id = payload.get("product_id")
    buyer_address = payload.get("buyer_address")
    amount_ton = payload.get("amount_ton")
    timeout_days = int(payload.get("timeout_days", 7))

    if not product_id or not isinstance(product_id, str):
        raise HTTPException(status_code=400, detail="product_id is required")
    if not buyer_address or not isinstance(buyer_address, str):
        raise HTTPException(status_code=400, detail="buyer_address is required")
    try:
        amount_ton_num = float(amount_ton)
    except Exception:
        raise HTTPException(status_code=400, detail="amount_ton must be a number")
    if amount_ton_num <= 0:
        raise HTTPException(status_code=400, detail="amount_ton must be positive")

    # Проверим наличие товара и не зарезервирован ли он уже
    product = await db.hub_offers.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.get("reserved"):
        raise HTTPException(status_code=409, detail="Product already reserved")

    # Создаём эскроу (симуляция в сервисе)
    try:
        deal = await _payment_service.create_escrow_deal(
            buyer_address=buyer_address,
            amount_ton=amount_ton_num,
            timeout_days=timeout_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.now(timezone.utc)
    reserved_until = now + timedelta(days=timeout_days)

    # Запишем сделку в коллекцию hub_deals
    deal_doc = {
        "deal_id": deal["deal_id"],
        "status": deal["status"],  # frozen
        "product_id": product_id,
        "seller": product.get("seller"),
        "buyer_address": buyer_address,
        "amount_ton": amount_ton_num,
        "amount_nano": deal["amount_nano"],
        "timeout_days": timeout_days,
        "reserved_at": now.isoformat(),
        "reserved_until": reserved_until.isoformat(),
        "contract_address": deal.get("contract_address"),
    }
    await db.hub_deals.update_one({"deal_id": deal_doc["deal_id"]}, {"$set": deal_doc}, upsert=True)

    # Обновим товар: пометим как зарезервированный
    await db.hub_offers.update_one(
        {"id": product_id},
        {
            "$set": {
                "reserved": True,
                "reserved_deal_id": deal_doc["deal_id"],
                "reserved_by": buyer_address,
                "reserved_until": reserved_until.isoformat(),
            }
        },
    )

    return {"status": "frozen", "deal": deal_doc}


@router.post("/payments/{deal_id}/confirm")
async def confirm_payment(deal_id: str) -> Dict[str, Any]:
    """Подтвердить доставку — освободить средства продавцу и завершить сделку."""
    check_enabled()

    deal = await db.hub_deals.find_one({"deal_id": deal_id})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.get("status") != "frozen":
        raise HTTPException(status_code=409, detail="Deal is not in frozen state")

    # Симуляция вызова смарт-контракта
    result = await confirm_delivery(deal_id)

    now = datetime.now(timezone.utc).isoformat()
    await db.hub_deals.update_one(
        {"deal_id": deal_id},
        {"$set": {"status": "released", "released_at": now, "release_tx": result}},
    )

    # Обновим карточку товара: снятие резерва, отметка о продаже
    await db.hub_offers.update_one(
        {"id": deal["product_id"]},
        {
            "$set": {
                "reserved": False,
                "sold": True,
                "sold_deal_id": deal_id,
            },
            "$unset": {
                "reserved_deal_id": "",
                "reserved_by": "",
                "reserved_until": "",
            },
        },
    )

    updated = await db.hub_deals.find_one({"deal_id": deal_id})
    return {"status": "released", "deal": updated}


@router.post("/payments/{deal_id}/refund")
async def refund_payment(deal_id: str) -> Dict[str, Any]:
    """Запросить возврат средств — снимаем бронь с товара."""
    check_enabled()

    deal = await db.hub_deals.find_one({"deal_id": deal_id})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.get("status") != "frozen":
        raise HTTPException(status_code=409, detail="Refund is only allowed for frozen deals")

    result = await request_refund(deal_id)

    now = datetime.now(timezone.utc).isoformat()
    await db.hub_deals.update_one(
        {"deal_id": deal_id},
        {"$set": {"status": "refund_requested", "refund_at": now, "refund_tx": result}},
    )

    # Снимем бронь с товара
    await db.hub_offers.update_one(
        {"id": deal["product_id"]},
        {
            "$set": {"reserved": False},
            "$unset": {"reserved_deal_id": "", "reserved_by": "", "reserved_until": ""},
        },
    )

    updated = await db.hub_deals.find_one({"deal_id": deal_id})
    return {"status": "refund_requested", "deal": updated}


@router.get("/payments/{deal_id}")
async def get_deal(deal_id: str) -> Dict[str, Any]:
    """Получить текущее состояние сделки (эскроу)."""
    check_enabled()
    deal = await db.hub_deals.find_one({"deal_id": deal_id})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal
