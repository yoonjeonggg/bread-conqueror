"""주간 미션 (로드맵 8단계).

진행도는 저장하지 않고 조회 시점에 이번 주(월요일 00:00 UTC 기준) flags/reviews
에서 계산한다. 보상은 (user, mission, week) 당 1회, `claim` 으로 잠근다.
라우터가 커밋을 소유한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FlagType, MissionMetric
from app.models.flag import Flag
from app.models.mission import MissionClaim, MissionDefinition
from app.models.review import Review
from app.models.store import Store
from app.models.user import User, UserStat
from app.services import tier_service


def current_week_start(today: date | None = None) -> date:
    today = today or datetime.utcnow().date()
    return today - timedelta(days=today.weekday())  # 월요일


@dataclass
class MissionView:
    code: str
    title: str
    description: str
    metric: MissionMetric
    target: int
    reward_exp: int
    progress: int
    completed: bool
    claimed: bool


@dataclass
class ClaimResult:
    code: str
    reward_exp: int
    exp: int
    tier_level: int
    tier_changed: bool


async def _progress(
    db: AsyncSession, user_id: int, metric: MissionMetric, since: datetime
) -> int:
    if metric is MissionMetric.REVIEWS:
        stmt = (
            select(func.count())
            .select_from(Review)
            .where(Review.user_id == user_id, Review.created_at >= since)
        )
    elif metric is MissionMetric.DISTINCT_REGIONS:
        stmt = (
            select(func.count(func.distinct(Store.region_sido)))
            .select_from(Flag)
            .join(Store, Store.id == Flag.store_id)
            .where(
                Flag.user_id == user_id,
                Flag.created_at >= since,
                Store.region_sido.isnot(None),
            )
        )
    else:
        stmt = select(
            func.count(func.distinct(Flag.store_id))
            if metric is MissionMetric.DISTINCT_STORES
            else func.count()
        ).select_from(Flag).where(
            Flag.user_id == user_id, Flag.created_at >= since
        )
        if metric is MissionMetric.GOLD_FLAGS:
            stmt = stmt.where(Flag.type == FlagType.GOLD)
        elif metric is MissionMetric.SILVER_FLAGS:
            stmt = stmt.where(Flag.type == FlagType.SILVER)

    return (await db.execute(stmt)).scalar_one() or 0


async def weekly_missions(
    db: AsyncSession, user_id: int
) -> tuple[date, list[MissionView]]:
    week = current_week_start()
    since = datetime.combine(week, datetime.min.time())

    defs = (
        (
            await db.execute(
                select(MissionDefinition)
                .where(MissionDefinition.active.is_(True))
                .order_by(MissionDefinition.sort_order, MissionDefinition.code)
            )
        )
        .scalars()
        .all()
    )
    claimed = set(
        (
            await db.execute(
                select(MissionClaim.mission_code).where(
                    MissionClaim.user_id == user_id,
                    MissionClaim.week_start == week,
                )
            )
        )
        .scalars()
        .all()
    )

    views: list[MissionView] = []
    for d in defs:
        raw = await _progress(db, user_id, d.metric, since)
        views.append(
            MissionView(
                code=d.code,
                title=d.title,
                description=d.description,
                metric=d.metric,
                target=d.target,
                reward_exp=d.reward_exp,
                progress=min(raw, d.target),
                completed=raw >= d.target,
                claimed=d.code in claimed,
            )
        )
    return week, views


async def claim(
    db: AsyncSession, *, user: User, mission_code: str
) -> ClaimResult:
    week = current_week_start()
    since = datetime.combine(week, datetime.min.time())

    mission = await db.get(MissionDefinition, mission_code)
    if mission is None or not mission.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="미션을 찾을 수 없습니다."
        )

    dupe = (
        await db.execute(
            select(MissionClaim.id).where(
                MissionClaim.user_id == user.id,
                MissionClaim.mission_code == mission_code,
                MissionClaim.week_start == week,
            )
        )
    ).scalar_one_or_none()
    if dupe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이번 주 보상을 이미 받았습니다.",
        )

    raw = await _progress(db, user.id, mission.metric, since)
    if raw < mission.target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"아직 완료되지 않았습니다 ({raw}/{mission.target}).",
        )

    db.add(
        MissionClaim(
            user_id=user.id,
            mission_code=mission_code,
            week_start=week,
            reward_exp=mission.reward_exp,
        )
    )
    stat = await db.get(UserStat, user.id)
    if stat is None:
        stat = UserStat(user_id=user.id)
        db.add(stat)
    stat.exp = (stat.exp or 0) + mission.reward_exp
    tier_changed = await tier_service.recalculate_tier(db, stat)
    await db.flush()

    return ClaimResult(
        code=mission_code,
        reward_exp=mission.reward_exp,
        exp=stat.exp,
        tier_level=stat.tier_level,
        tier_changed=tier_changed,
    )
