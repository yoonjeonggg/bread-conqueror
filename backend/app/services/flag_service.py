"""Conquest / flag creation (F-CONQ-01~09).

One `create_flag` call is a single transaction that touches Flag, UserStat,
StoreStat and (via tier_service) the user's tier. The router owns the
commit; this module never commits so the whole flow stays atomic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvidenceType, FlagType
from app.models.flag import Flag
from app.models.store import Store, StoreStat
from app.models.user import User, UserStat
from app.services import policy_service, tier_service
from app.services.abuse_detection import evaluate_conquest
from app.services.geo_service import haversine_m


@dataclass
class ConquestResult:
    flag: Flag
    exp_granted: int
    tier_changed: bool
    new_tier_level: int
    upgraded_from_silver: bool
    is_flagged: bool
    abuse_reasons: list[str]


_COUNTER_FIELDS = (
    "exp",
    "gold_flag_count",
    "silver_flag_count",
    "conquered_store_count",
    "conqueror_count",
    "review_count",
    "received_like_count",
    "tier_level",
)


def _zero_counters(stat: object) -> None:
    for field in _COUNTER_FIELDS:
        if hasattr(stat, field) and getattr(stat, field) is None:
            setattr(stat, field, 1 if field == "tier_level" else 0)


def _naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


async def _last_flag(db: AsyncSession, user_id: int) -> Flag | None:
    return (
        await db.execute(
            select(Flag)
            .where(Flag.user_id == user_id)
            .order_by(Flag.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _check_cooldown(
    db: AsyncSession, user_id: int, store_id: int
) -> None:
    hours = await policy_service.get_int(db, "COOLDOWN_HOURS")
    since = datetime.utcnow() - timedelta(hours=hours)
    recent = (
        await db.execute(
            select(func.count())
            .select_from(Flag)
            .where(
                Flag.user_id == user_id,
                Flag.store_id == store_id,
                Flag.created_at >= since,
            )
        )
    ).scalar_one()
    if recent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이 매장은 {hours}시간 쿨다운 중입니다.",
        )


async def _check_silver_limits(db: AsyncSession, user_id: int) -> None:
    daily_limit = await policy_service.get_int(db, "SILVER_DAILY_LIMIT")
    total_limit = await policy_service.get_int(db, "SILVER_TOTAL_LIMIT")
    day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    today = (
        await db.execute(
            select(func.count())
            .select_from(Flag)
            .where(
                Flag.user_id == user_id,
                Flag.type == FlagType.SILVER,
                Flag.created_at >= day_start,
            )
        )
    ).scalar_one()
    if today >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"실버 깃발은 하루 {daily_limit}개까지 등록할 수 있습니다.",
        )

    total = (
        await db.execute(
            select(func.count())
            .select_from(Flag)
            .where(Flag.user_id == user_id, Flag.type == FlagType.SILVER)
        )
    ).scalar_one()
    if total >= total_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"실버 깃발 누적 등록 한도({total_limit}개)를 초과했습니다.",
        )


async def create_flag(
    db: AsyncSession,
    *,
    user: User,
    store: Store,
    flag_type: FlagType,
    lat: float | None,
    lng: float | None,
    evidence_type: EvidenceType,
    evidence_image_url: str | None,
    visited_at: datetime | None,
    via_qr: bool = False,
) -> ConquestResult:
    now = datetime.utcnow()
    await _check_cooldown(db, user.id, store.id)

    user_stat = await db.get(UserStat, user.id)
    store_stat = await db.get(StoreStat, store.id)
    if user_stat is None:
        user_stat = UserStat(user_id=user.id)
        db.add(user_stat)
    if store_stat is None:
        store_stat = StoreStat(store_id=store.id)
        db.add(store_stat)

    _zero_counters(user_stat)
    _zero_counters(store_stat)

    gold_exp = await policy_service.get_int(db, "GOLD_EXP")
    silver_ratio = await policy_service.get_float(db, "SILVER_EXP_RATIO")
    max_speed = await policy_service.get_float(db, "ABUSE_SPEED_KMH")

    is_flagged = False
    abuse_reasons: list[str] = []

    if flag_type is FlagType.GOLD and via_qr:
        # 매장에 붙은 QR을 스캔했다는 것 자체가 현장 방문 증빙이므로
        # 반경/속도 검사를 건너뛴다.
        if evidence_type is EvidenceType.NONE:
            evidence_type = EvidenceType.QR
        exp_granted = gold_exp
    elif flag_type is FlagType.GOLD:
        if lat is None or lng is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="골드 깃발은 GPS 좌표가 필요합니다.",
            )
        radius = await policy_service.get_int(db, "CONQUEST_RADIUS_M")
        distance = haversine_m(lat, lng, float(store.lat), float(store.lng))
        if distance > radius:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"매장 반경 {radius}m 밖입니다 (현재 약 {distance:.0f}m). "
                    "매장 근처에서 다시 시도해 주세요."
                ),
            )
        if evidence_type is EvidenceType.NONE:
            evidence_type = EvidenceType.REALTIME_GPS
        exp_granted = gold_exp

        prev = await _last_flag(db, user.id)
        signal = evaluate_conquest(
            new_lat=lat,
            new_lng=lng,
            new_time=now,
            prev_lat=float(prev.lat_at_conquest)
            if prev and prev.lat_at_conquest is not None
            else None,
            prev_lng=float(prev.lng_at_conquest)
            if prev and prev.lng_at_conquest is not None
            else None,
            prev_time=_naive_utc(prev.created_at) if prev else None,
            max_speed_kmh=max_speed,
        )
        is_flagged = signal.is_suspicious
        abuse_reasons = signal.reasons
    else:
        await _check_silver_limits(db, user.id)
        exp_granted = int(gold_exp * silver_ratio)

    # First-ever flag by this user at this store? (before we insert the new one)
    prior_here = (
        await db.execute(
            select(func.count())
            .select_from(Flag)
            .where(Flag.user_id == user.id, Flag.store_id == store.id)
        )
    ).scalar_one()
    first_conquest_here = prior_here == 0

    # Silver -> Gold upgrade: promote an existing valid silver flag at this store.
    upgraded = False
    if flag_type is FlagType.GOLD:
        silver_flag = (
            await db.execute(
                select(Flag).where(
                    Flag.user_id == user.id,
                    Flag.store_id == store.id,
                    Flag.type == FlagType.SILVER,
                )
            )
        ).scalars().first()
        if silver_flag is not None:
            upgraded = True
            user_stat.silver_flag_count = max(0, user_stat.silver_flag_count - 1)
            store_stat.silver_flag_count = max(0, store_stat.silver_flag_count - 1)

    flag = Flag(
        user_id=user.id,
        store_id=store.id,
        type=flag_type,
        evidence_type=evidence_type,
        evidence_image_url=evidence_image_url,
        visited_at=visited_at,
        lat_at_conquest=lat,
        lng_at_conquest=lng,
        exp_granted=exp_granted,
        is_flagged=is_flagged,
        upgraded_from_silver=upgraded,
    )
    db.add(flag)

    user_stat.exp += exp_granted
    if flag_type is FlagType.GOLD:
        user_stat.gold_flag_count += 1
        store_stat.gold_flag_count += 1
    else:
        user_stat.silver_flag_count += 1
        store_stat.silver_flag_count += 1

    if first_conquest_here:
        user_stat.conquered_store_count += 1
        store_stat.conqueror_count += 1

    tier_changed = await tier_service.recalculate_tier(db, user_stat)

    await db.flush()

    return ConquestResult(
        flag=flag,
        exp_granted=exp_granted,
        tier_changed=tier_changed,
        new_tier_level=user_stat.tier_level,
        upgraded_from_silver=upgraded,
        is_flagged=is_flagged,
        abuse_reasons=abuse_reasons,
    )
