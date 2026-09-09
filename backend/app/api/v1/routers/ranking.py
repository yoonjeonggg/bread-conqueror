from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.dependencies import DbSession, OptionalUser
from app.core.redis import redis_client
from app.models.user import User, UserStat
from app.schemas.ranking import RankingEntry, RankingResponse
from app.services import ranking_service

router = APIRouter(prefix="/rankings", tags=["rankings"])


async def _entries_from_db(
    db: DbSession, region_sido: str | None, limit: int
) -> list[RankingEntry]:
    """DB fallback for when Redis has no data yet (F-RANK, source of truth)."""
    stmt = (
        select(User.id, User.nickname, UserStat.tier_level, UserStat.exp)
        .join(UserStat, UserStat.user_id == User.id)
        .order_by(UserStat.exp.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        RankingEntry(
            rank=i + 1,
            user_id=r.id,
            nickname=r.nickname,
            tier_level=r.tier_level,
            exp=r.exp,
        )
        for i, r in enumerate(rows)
    ]


@router.get("/national", response_model=RankingResponse)
async def national_ranking(
    db: DbSession,
    user: OptionalUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RankingResponse:
    top = await ranking_service.top(redis_client, limit)
    if top:
        ids = [uid for uid, _ in top]
        name_map = dict(
            (
                await db.execute(
                    select(User.id, User.nickname).where(User.id.in_(ids))
                )
            ).all()
        )
        tier_map = dict(
            (
                await db.execute(
                    select(UserStat.user_id, UserStat.tier_level).where(
                        UserStat.user_id.in_(ids)
                    )
                )
            ).all()
        )
        entries = [
            RankingEntry(
                rank=i + 1,
                user_id=uid,
                nickname=name_map.get(uid, f"user{uid}"),
                tier_level=tier_map.get(uid, 1),
                exp=int(score),
            )
            for i, (uid, score) in enumerate(top)
        ]
    else:
        entries = await _entries_from_db(db, None, limit)

    my_rank = (
        await ranking_service.get_rank(redis_client, user.id) if user else None
    )
    return RankingResponse(scope="national", entries=entries, my_rank=my_rank)


@router.get("/regional", response_model=RankingResponse)
async def regional_ranking(
    region_sido: str,
    db: DbSession,
    user: OptionalUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RankingResponse:
    entries = await _entries_from_db(db, region_sido, limit)
    my_rank = (
        await ranking_service.get_rank(redis_client, user.id, region_sido)
        if user
        else None
    )
    return RankingResponse(
        scope="regional", region_sido=region_sido, entries=entries, my_rank=my_rank
    )
