# services/trust_service.py
from database import db
from typing import Dict, List

async def add_trust(source: str, target: str, weight: float):
    """
    Добавляет связь доверия в локальную БД и рассылает по сети
    """
    trust_doc = {
        "source": source,
        "target": target,
        "weight": max(0.1, min(1.0, weight)),  # ограничение
        "timestamp": "2025-04-05T12:00:00Z"
    }
    await db.trust_log.insert_one(trust_doc)
    return trust_doc

async def get_direct_trust(source: str, target: str) -> float:
    doc = await db.trust_log.find_one({"source": source, "target": target})
    return doc["weight"] if doc else 0.0

async def compute_trust_score(source: str, target: str, depth: int = 3) -> float:
    """
    Рекурсивный расчёт доверия через цепочки
    """
    if depth == 0:
        return 0.0
    if source == target:
        return 1.0

    direct = await get_direct_trust(source, target)
    if direct > 0:
        return direct

    # Поиск через посредников
    total_trust = 0.0
    async for relay in db.trust_log.find({"source": source}):
        relay_weight = relay["weight"]
        path_trust = await compute_trust_score(relay["target"], target, depth - 1)
        if path_trust > 0:
            # Умножаем веса и добавляем с затуханием
            total_trust = max(total_trust, relay_weight * path_trust * 0.8)

    return total_trust

async def is_spam_report(reporter: str, target: str) -> bool:
    """
    Проверяет, достаточно ли доверия у репортёра
    """
    trust_score = await compute_trust_score(reporter, target)
    return trust_score >= 0.3  # порог
