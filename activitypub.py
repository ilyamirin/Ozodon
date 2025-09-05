"""ActivityPub helper builders for Ozodon.

This module provides small helper functions to construct ActivityPub-compatible
objects used by the application (Offer and custom Trust activities). The
functions are intentionally pure and side-effect free to simplify testing and
reuse.

All functions return plain Python dictionaries ready to be serialized to JSON.
"""
from typing import Any, Dict, List, Union


def context() -> List[Union[str, Dict[str, str]]]:
    """Return a list suitable for the @context of ActivityPub objects.

    The context includes standard ActivityStreams and abbreviations used by
    schema.org as well as a custom namespace for federated-market vocabulary.
    """
    return [
        "https://www.w3.org/ns/activitystreams",
        {
            "schema": "https://schema.org/",
            "sec": "https://w3id.org/security#",
            "ldp": "http://www.w3.org/ns/ldp#",
            "fedmarket": "https://vocab.fedmarket.example#",
        },
    ]


def activity_base(type_: str, actor: str) -> Dict[str, Any]:
    """Build a base ActivityPub activity skeleton.

    Args:
        type_: The Activity type (e.g., "Offer").
        actor: The actor ID (URL) performing the activity.

    Returns:
        A dictionary with common ActivityPub fields.

    Notes:
        The published field is a placeholder and should be set by the caller to
        the actual timestamp if required.
    """
    return {
        "@context": context(),
        "type": type_,
        "actor": actor,
        # Placeholder timestamp; production code should override with real time
        "published": "2025-04-05T12:00:00Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    }


def make_offer(actor: str, product: Dict[str, Any]) -> Dict[str, Any]:
    """Construct an ActivityPub Offer for a product.

    Args:
        actor: Actor URL of the seller issuing the offer.
        product: A mapping with keys name, description, optional image, price,
            optional currency (defaults to RUB), and optional tags.

    Returns:
        A fully-formed Offer activity dictionary.

    Implementation details:
        - Ensures tags are a list of strings and converts them to Hashtag
          objects with leading '#'.
        - Adds a default '#market' tag to improve discovery.
    """
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
            "schema:availability": "https://schema.org/InStock",
        },
    }
    # Normalize tags input to a list of strings
    tags = product.get("tags", ["handmade"])  # sensible default
    if isinstance(tags, str):
        tags = [tags]
    activity["tag"] = (
        [{"type": "Hashtag", "name": "#market"}]
        + [{"type": "Hashtag", "name": f"#{tag}"} for tag in tags]
    )
    return activity


def make_trust(actor: str, target: str, weight: float) -> Dict[str, Any]:
    """Construct a custom Trust activity linking actor to target with weight.

    Args:
        actor: URL of the entity issuing the trust statement.
        target: URL of the entity that is being trusted.
        weight: A floating value from 0 to 1 indicating trust strength.

    Returns:
        A federated-market Trust activity as a dictionary.
    """
    return {
        "@context": context(),
        "type": "fedmarket:Trust",
        "actor": actor,
        "object": {
            "type": "fedmarket:TrustRelationship",
            "target": target,
            "weight": weight,
            "issued": "2025-04-05T12:00:00Z",
        },
        "published": "2025-04-05T12:00:00Z",
    }
