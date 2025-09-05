"""Pydantic models used throughout the Ozodon application.

Models define validation and structure for trust links, products, and queries.
All fields are annotated with types and sensible defaults where appropriate.
"""
from typing import Optional

from pydantic import BaseModel


class TrustLink(BaseModel):
    """Represents a directed trust relationship with a weighted score."""

    source: str
    target: str
    weight: float
    proof_signature: str


class Product(BaseModel):
    """Represents a marketplace product indexed by the hub."""

    id: str
    name: str
    description: str
    image: Optional[str] = None
    price: str
    currency: str = "TON"


class SearchQuery(BaseModel):
    """Parameters for searching products in the hub index."""

    q: Optional[str] = None
    tag: str = ""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = 20
