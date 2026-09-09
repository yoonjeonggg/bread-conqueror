import pytest

from app.models.user import UserStat
from app.services import tier_service


@pytest.mark.asyncio
async def test_tier_starts_at_one(db_session) -> None:
    stat = UserStat(user_id=1, exp=0)
    assert await tier_service.calculate_tier_level(db_session, stat) == 1


@pytest.mark.asyncio
async def test_tier_climbs_with_exp(db_session) -> None:
    stat = UserStat(user_id=1, exp=1500, gold_flag_count=10, silver_flag_count=5)
    assert await tier_service.calculate_tier_level(db_session, stat) == 3


@pytest.mark.asyncio
async def test_upper_tier_gated_by_gold_ratio(db_session) -> None:
    # Enough exp for tier 4 but only 40% gold -> capped at tier 3.
    stat = UserStat(user_id=1, exp=5000, gold_flag_count=4, silver_flag_count=6)
    assert await tier_service.calculate_tier_level(db_session, stat) == 3

    stat.gold_flag_count = 8
    stat.silver_flag_count = 2
    assert await tier_service.calculate_tier_level(db_session, stat) == 4


@pytest.mark.asyncio
async def test_recalculate_reports_change(db_session) -> None:
    stat = UserStat(user_id=1, exp=400, tier_level=1)
    assert await tier_service.recalculate_tier(db_session, stat) is True
    assert stat.tier_level == 2
    assert await tier_service.recalculate_tier(db_session, stat) is False
