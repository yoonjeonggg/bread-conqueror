"""리뷰 집계 (F-DETAIL-01, F-DETAIL-02, F-PROF-01).

리뷰가 생성/수정/삭제될 때 StoreStat.average_rating 과 UserStat.review_count 를
같은 트랜잭션 안에서 다시 계산한다. 라우터가 커밋을 소유한다.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review
from app.models.store import StoreStat
from app.models.user import UserStat


async def recompute_store_rating(db: AsyncSession, store_id: int) -> None:
    avg = (
        await db.execute(
            select(func.avg(Review.rating)).where(Review.store_id == store_id)
        )
    ).scalar_one_or_none()

    stat = await db.get(StoreStat, store_id)
    if stat is None:
        stat = StoreStat(store_id=store_id)
        db.add(stat)
    stat.average_rating = (
        Decimal(str(round(float(avg), 1))) if avg is not None else None
    )


async def recompute_user_review_count(db: AsyncSession, user_id: int) -> None:
    count = (
        await db.execute(
            select(func.count()).select_from(Review).where(Review.user_id == user_id)
        )
    ).scalar_one()

    stat = await db.get(UserStat, user_id)
    if stat is None:
        stat = UserStat(user_id=user_id)
        db.add(stat)
    stat.review_count = count
