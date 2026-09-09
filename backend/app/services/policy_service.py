"""Reads runtime policy values from the policy_configs table (with safe defaults)."""

from __future__ import annotations

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


async def get_config(db: AsyncSession, key: str) -> str:
    row = await db.get(PolicyConfig, key)
    if row is not None:
        return row.config_value
    return DEFAULTS[key]


async def get_int(db: AsyncSession, key: str) -> int:
    return int(float(await get_config(db, key)))


async def get_float(db: AsyncSession, key: str) -> float:
    return float(await get_config(db, key))


async def all_configs(db: AsyncSession) -> dict[str, str]:
    result = {**DEFAULTS}
    rows = (await db.execute(select(PolicyConfig))).scalars().all()
    for row in rows:
        result[row.config_key] = row.config_value
    return result
