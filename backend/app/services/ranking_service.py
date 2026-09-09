"""Ranking via Redis Sorted Sets (F-RANK-01~03).

Writes are best-effort: a Redis outage must not break a conquest. A periodic
task (app/tasks) rebuilds the ZSETs from the DB as the source of truth.
"""

from __future__ import annotations

from redis.asyncio import Redis

NATIONAL_KEY = "rank:national"


def _region_key(region_sido: str) -> str:
    return f"rank:region:{region_sido}"


async def set_score(
    redis: Redis, user_id: int, exp: int, region_sido: str | None = None
) -> None:
    try:
        pipe = redis.pipeline()
        pipe.zadd(NATIONAL_KEY, {str(user_id): exp})
        if region_sido:
            pipe.zadd(_region_key(region_sido), {str(user_id): exp})
        await pipe.execute()
    except Exception:  # noqa: BLE001 - ranking is non-critical
        pass


async def get_rank(redis: Redis, user_id: int, region_sido: str | None = None) -> int | None:
    key = _region_key(region_sido) if region_sido else NATIONAL_KEY
    rank = await redis.zrevrank(key, str(user_id))
    return rank + 1 if rank is not None else None


async def top(
    redis: Redis, limit: int = 50, region_sido: str | None = None
) -> list[tuple[int, float]]:
    key = _region_key(region_sido) if region_sido else NATIONAL_KEY
    rows = await redis.zrevrange(key, 0, limit - 1, withscores=True)
    return [(int(uid), score) for uid, score in rows]


async def friends_rank(
    redis: Redis, user_ids: list[int]
) -> list[tuple[int, float]]:
    if not user_ids:
        return []
    scores = await redis.zmscore(NATIONAL_KEY, [str(u) for u in user_ids])
    paired = [
        (uid, score)
        for uid, score in zip(user_ids, scores, strict=True)
        if score is not None
    ]
    return sorted(paired, key=lambda x: x[1], reverse=True)
