"""Reads runtime policy values from the policy_configs table (with safe defaults).

`policy_configs` has a handful of rows that change only via a manual DB edit, but
`get_config`/`get_int`/`get_float` are called several times per conquest
(`flag_service.py`). A single request-independent, process-local cache with a short
TTL avoids re-querying that tiny table on every call while still picking up manual
changes within a bounded delay.
"""

from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import PolicyConfig

DEFAULTS: dict[str, str] = {
    "CONQUEST_RADIUS_M": "50",
    "COOLDOWN_HOURS": "24",
    "SILVER_DAILY_LIMIT": "5",
    "SILVER_TOTAL_LIMIT": "30",
    "TIER4_GOLD_RATIO": "0.70",
    "GOLD_EXP": "100",
    "SILVER_EXP_RATIO": "0.5",
    "ABUSE_SPEED_KMH": "150",
}

_CACHE_TTL_SECONDS = 60
_cache: dict[str, str] | None = None
_cached_at = 0.0


def invalidate_cache() -> None:
    global _cache, _cached_at
    _cache = None
    _cached_at = 0.0


async def all_configs(db: AsyncSession) -> dict[str, str]:
    global _cache, _cached_at
    now = time.monotonic()
    if _cache is None or (now - _cached_at) > _CACHE_TTL_SECONDS:
        result = {**DEFAULTS}
        rows = (await db.execute(select(PolicyConfig))).scalars().all()
        for row in rows:
            result[row.config_key] = row.config_value
        _cache = result
        _cached_at = now
    return _cache


async def get_config(db: AsyncSession, key: str) -> str:
    configs = await all_configs(db)
    return configs.get(key, DEFAULTS[key])


async def get_int(db: AsyncSession, key: str) -> int:
    return int(float(await get_config(db, key)))


async def get_float(db: AsyncSession, key: str) -> float:
    return float(await get_config(db, key))
