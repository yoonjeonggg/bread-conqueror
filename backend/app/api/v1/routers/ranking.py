from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession, OptionalUser
from app.core.redis import redis_client
from app.models.flag import Flag
from app.models.social import Follow
from app.models.store import Store
from app.models.user import User, UserStat
from app.schemas.ranking import RankingEntry, RankingResponse
from app.services import ranking_service

router = APIRouter(prefix="/rankings", tags=["rankings"])


async def _entries_from_db(
    db: DbSession, region_sido: str | None, limit: int
) -> list[RankingEntry]:
    """DB fallback for when Redis has no data yet (F-RANK, source of truth).

    지역 랭킹은 해당 지역 매장에서 깃발을 꽂은 적 있는 사용자만 대상으로 한다
    (사용자 자체에는 지역 정보가 없음 — 활동 지역을 기준으로 삼는다).
    """
    stmt = (
        select(User.id, User.nickname, UserStat.tier_level, UserStat.exp)
        .join(UserStat, UserStat.user_id == User.id)
        .order_by(UserStat.exp.desc())
        .limit(limit)
    )
    if region_sido:
        region_user_ids = (
            select(Flag.user_id.distinct())
            .join(Store, Store.id == Flag.store_id)
            .where(Store.region_sido == region_sido)
        )
        stmt = stmt.where(User.id.in_(region_user_ids))

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


async def _build_ranking(
    db: DbSession, user: User | None, limit: int, region_sido: str | None = None
) -> RankingResponse:
    top = await ranking_service.top(redis_client, limit, region_sido)
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
        entries = await _entries_from_db(db, region_sido, limit)

    my_rank = (
        await ranking_service.get_rank(redis_client, user.id, region_sido)
        if user
        else None
    )
    return RankingResponse(
        scope="regional" if region_sido else "national",
        region_sido=region_sido,
        entries=entries,
        my_rank=my_rank,
    )


@router.get("/national", response_model=RankingResponse)
async def national_ranking(
    db: DbSession,
    user: OptionalUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RankingResponse:
    return await _build_ranking(db, user, limit)


@router.get("/regional", response_model=RankingResponse)
async def regional_ranking(
    region_sido: str,
    db: DbSession,
    user: OptionalUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RankingResponse:
    return await _build_ranking(db, user, limit, region_sido)


@router.get("/friends", response_model=RankingResponse)
async def friends_ranking(db: DbSession, user: CurrentUser) -> RankingResponse:
    """F-RANK-03 — 내가 팔로우한 사람 + 나, exp 내림차순."""
    followee_ids = (
        (
            await db.execute(
                select(Follow.followee_id).where(Follow.follower_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    ids = [*followee_ids, user.id]

    rows = (
        await db.execute(
            select(User.id, User.nickname, UserStat.tier_level, UserStat.exp)
            .join(UserStat, UserStat.user_id == User.id)
            .where(User.id.in_(ids))
            .order_by(UserStat.exp.desc())
        )
    ).all()

    entries = [
        RankingEntry(
            rank=i + 1,
            user_id=r.id,
            nickname=r.nickname,
            tier_level=r.tier_level,
            exp=r.exp,
        )
        for i, r in enumerate(rows)
    ]
    my_rank = next((e.rank for e in entries if e.user_id == user.id), None)
    return RankingResponse(scope="friends", entries=entries, my_rank=my_rank)
