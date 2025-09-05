# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pathlib import Path

from database import db, ping_db
from activitypub import make_offer, make_trust
from services.ton_payment import TONPaymentService
from services.trust_service import add_trust, compute_trust_score
import models

app = FastAPI(title="FedMarket Node")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ton_service = TONPaymentService()

@app.on_event("startup")
async def startup():
    await ping_db()

@app.get("/", response_class=PlainTextResponse)
async def read_root():
    """Serve README.md content at the root URL."""
    try:
        readme_path = Path(__file__).parent / "README.md"
        content = readme_path.read_text(encoding="utf-8")
        return PlainTextResponse(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load README: {e}")

@app.post("/inbox")
async def inbox(activity: dict):
    atype = activity.get("type")
    actor = activity.get("actor")

    if atype == "Offer":
        obj = activity.get("object", {})
        product_data = {
            "id": obj.get("id") or activity.get("id"),
            "name": obj.get("schema:name", "No name"),
            "description": obj.get("schema:description", ""),
            "image": obj.get("schema:image"),
            "price": obj.get("schema:offers", {}).get("schema:price", "0"),
            "currency": obj.get("schema:offers", {}).get("schema:priceCurrency", "TON"),
            "tags": [t["name"].lstrip("#") for t in activity.get("tag", [])]
        }
        await db.offers.insert_one(activity)
        await db.products.insert_one(product_data)
        return {"status": "offer_saved"}

    elif atype == "fedmarket:Trust":
        target = activity["object"]["target"]
        weight = activity["object"]["weight"]
        await add_trust(actor, target, weight)
        return {"status": "trust_recorded"}

    elif atype == "Flag":
        reporter = actor
        flagged = activity["object"]["id"]
        if await compute_trust_score(reporter, flagged) >= 0.3:
            await db.flags.insert_one(activity)
            return {"status": "flag_accepted (trusted)"}
        else:
            return {"status": "flag_ignored (low trust)"}

    return {"status": "ignored"}

@app.get("/products")
async def list_products():
    products = await db.products.find().to_list(100)
    return {"products": products}

@app.post("/trust")
async def create_trust(trust: models.TrustLink):
    activity = make_trust(trust.source, trust.target, trust.weight)
    # Здесь можно подписать activity
    await add_trust(trust.source, trust.target, trust.weight)
    # Рассылаем в outbox (упрощённо — просто возвращаем)
    return {"activity": activity, "status": "trust_broadcast_initiated"}

@app.post("/pay/escrow")
async def create_escrow(buyer_addr: str, amount: float):
    deal = await ton_service.create_escrow_deal(buyer_addr, amount)
    return deal
