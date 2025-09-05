# models.py
from typing import Optional

from pydantic import BaseModel


class TrustLink(BaseModel):
    source: str
    target: str
    weight: float
    proof_signature: str

class Product(BaseModel):
    id: str
    name: str
    description: str
    image: Optional[str] = None
    price: str
    currency: str = "TON"

class SearchQuery(BaseModel):
    q: Optional[str] = None
    tag: str = ""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = 20
