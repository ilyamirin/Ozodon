"""Trust graph utilities for computing trust-based scores.

Implements basic operations over a trust log stored in MongoDB. The algorithm is
simple by design and uses bounded recursion with dampening to prevent runaway
values while still capturing multi-hop trust.
"""
from typing import Dict, List

from database import db


async def add_trust(source: str, target: str, weight: float) -> Dict[str, object]:
    """Add a direct trust edge to the local trust log.

    Args:
        source: Actor issuing the trust statement.
        target: Actor receiving trust.
        weight: Strength in [0.1, 1.0]; will be clamped to this range.
    """
    trust_doc: Dict[str, object] = {
        "source": source,
        "target": target,
        "weight": max(0.1, min(1.0, float(weight))),  # clamp and coerce
        "timestamp": "2025-04-05T12:00:00Z",
    }
    await db.trust_log.insert_one(trust_doc)
    return trust_doc


async def get_direct_trust(source: str, target: str) -> float:
    """Return the direct trust weight from source to target, if any."""
    doc = await db.trust_log.find_one({"source": source, "target": target})
    return float(doc["weight"]) if doc else 0.0


async def compute_trust_score(source: str, target: str, depth: int = 3) -> float:
    """Compute a trust score from source to target via damped multi-hop paths.

    The recursion explores outgoing edges up to a limited depth and applies
    a decay factor to favor shorter/stronger paths and prevent inflation.
    """
    if depth == 0:
        return 0.0
    if source == target:
        return 1.0

    direct = await get_direct_trust(source, target)
    if direct > 0:
        return float(direct)

    # Explore via relays with dampening
    total_trust = 0.0
    async for relay in db.trust_log.find({"source": source}):
        relay_weight = float(relay["weight"])  # weight in [0,1]
        path_trust = await compute_trust_score(relay["target"], target, depth - 1)
        if path_trust > 0:
            # Multiply weights along the path and apply additional damping (0.8)
            total_trust = max(total_trust, relay_weight * path_trust * 0.8)

    return float(total_trust)


async def is_spam_report(reporter: str, target: str) -> bool:
    """Check if the reporter has enough trust to report the target.

    Uses a threshold over the computed trust score.
    """
    trust_score = await compute_trust_score(reporter, target)
    return trust_score >= 0.3  # порог
