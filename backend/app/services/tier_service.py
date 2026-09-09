"""Tier calculation (F-TIER-01~03).

Tier is derived from accumulated exp, gated by a gold-flag-ratio requirement on
the upper tiers. Policy values live in the tier_policies table so admins can tune
them without a deploy.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import TierPolicy
from app.models.user import UserStat

# Fallback ladder if tier_policies has not been seeded yet.
DEFAULT_LADDER: list[tuple[int, str, int, float | None]] = [
    (1, "빵 입문자", 0, None),
    (2, "빵 탐험가", 300, None),
    (3, "지역 정복자", 1200, None),
    (4, "전국 정복자", 4000, 0.70),
    (5, "전설의 빵 정복자", 12000, 0.70),
]


async def _ladder(db: AsyncSession) -> list[tuple[int, str, int, float | None]]:
    rows = (
        (await db.execute(select(TierPolicy).order_by(TierPolicy.tier_level)))
        .scalars()
        .all()
    )
    if not rows:
        return DEFAULT_LADDER
    return [
        (
            r.tier_level,
            r.tier_name,
            r.required_exp,
            float(r.gold_ratio_requirement)
            if r.gold_ratio_requirement is not None
            else None,
        )
        for r in rows
    ]


def _gold_ratio(stat: UserStat) -> float:
    gold = stat.gold_flag_count or 0
    total = gold + (stat.silver_flag_count or 0)
    return gold / total if total else 0.0


async def calculate_tier_level(db: AsyncSession, stat: UserStat) -> int:
    ladder = await _ladder(db)
    ratio = _gold_ratio(stat)
    exp = stat.exp or 0
    achieved = 1
    for level, _name, required_exp, gold_req in ladder:
        if exp < required_exp:
            break
        if gold_req is not None and ratio < gold_req:
            break
        achieved = level
    return achieved


async def recalculate_tier(db: AsyncSession, stat: UserStat) -> bool:
    """Update stat.tier_level in place. Returns True if the tier changed."""
    new_level = await calculate_tier_level(db, stat)
    if new_level != (stat.tier_level or 1):
        stat.tier_level = new_level
        return True
    return False


async def tier_name(db: AsyncSession, level: int) -> str:
    for lvl, name, _exp, _gold in await _ladder(db):
        if lvl == level:
            return name
    return "빵 입문자"
