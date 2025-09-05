# activitypub.py
from typing import Dict, Any, List, Union

def context() -> List[Union[str, Dict[str, str]]]:
    return [
        "https://www.w3.org/ns/activitystreams",
        {
            "schema": "https://schema.org/",
            "sec": "https://w3id.org/security#",
            "ldp": "http://www.w3.org/ns/ldp#",
            "fedmarket": "https://vocab.fedmarket.example#"
        }
    ]

def activity_base(type_: str, actor: str) -> Dict[str, Any]:
    return {
        "@context": context(),
        "type": type_,
        "actor": actor,
        "published": "2025-04-05T12:00:00Z",  # will be updated
        "to": ["https://www.w3.org/ns/activitystreams#Public"]
    }

def make_offer(actor: str, product: Dict[str, Any]) -> Dict[str, Any]:
    activity = activity_base("Offer", actor)
    activity["object"] = {
        "type": "schema:Product",
        "schema:name": product["name"],
        "schema:description": product["description"],
        "schema:image": product.get("image"),
        "schema:offers": {
            "type": "schema:Offer",
            "schema:price": product["price"],
            "schema:priceCurrency": product.get("currency", "RUB"),
            "schema:availability": "https://schema.org/InStock"
        }
    }
    tags = product.get("tags", ["handmade"])  # ensure list of strings
    if isinstance(tags, str):
        tags = [tags]
    activity["tag"] = (
        [{"type": "Hashtag", "name": "#market"}] +
        [{"type": "Hashtag", "name": f"#{tag}"} for tag in tags]
    )
    return activity

def make_trust(actor: str, target: str, weight: float):
    return {
        "@context": context(),
        "type": "fedmarket:Trust",
        "actor": actor,
        "object": {
            "type": "fedmarket:TrustRelationship",
            "target": target,
            "weight": weight,
            "issued": "2025-04-05T12:00:00Z"
        },
        "published": "2025-04-05T12:00:00Z"
    }
