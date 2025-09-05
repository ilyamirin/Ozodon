# models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TrustLink(BaseModel):
    source: str  # actor ID
    target: str
    weight: float  # 0.0 — 1.0
    proof_signature: str

class Product(BaseModel):
    id: str
    name: str
    description: str
    image: Optional[str] = None
    price: str
    currency: str = "RUB"

class Offer(BaseModel):
    actor: str
    object: Product
    to: List[str] = ["https://www.w3.org/ns/activitystreams#Public"]
    tag: List[Dict] = []
