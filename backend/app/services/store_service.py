"""매장 병합 (F-ADMIN-04).

중복 등록된 매장을 하나로 합친다. `source` 의 모든 참조(flags·reviews·claims·
QR 토큰·게시글)를 `target` 으로 옮기고, target 의 집계를 다시 계산한 뒤 source 를
CLOSED 처리한다. 라우터가 커밋을 소유한다 (이 모듈은 flush 만).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FlagType, StoreStatus
from app.models.flag import Flag
from app.models.post import Post
from app.models.review import Review
from app.models.store import Store, StoreStat
from app.models.store_claim import StoreClaim
from app.models.store_qr_token import StoreQrToken
from app.services import review_service


@dataclass
class MergeResult:
    target_id: int
    source_id: int
    moved_flags: int
    moved_reviews: int
    dropped_duplicate_reviews: int
    moved_posts: int
    moved_claims: int
    moved_qr_tokens: int
    owner_inherited: bool


async def _count(db: AsyncSession, *where) -> int:
    stmt = select(func.count()).select_from(Flag)
    for w in where:
        stmt = stmt.where(w)
    return (await db.execute(stmt)).scalar_one()


async def merge_stores(
    db: AsyncSession, *, target: Store, source: Store
) -> MergeResult:
    if target.id == source.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="같은 매장은 병합할 수 없습니다.",
        )
    if source.status == StoreStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 폐점(병합) 처리된 매장입니다.",
        )

    # 리뷰: (user_id, store_id) 유니크. 두 매장 모두 남긴 사용자는 source 리뷰를 버린다.
    # (MySQL 은 같은 테이블을 서브쿼리로 참조하는 DELETE/UPDATE 를 막으므로 ORM 루프로 처리)
    target_reviewers = set(
        (
            await db.execute(
                select(Review.user_id).where(Review.store_id == target.id)
            )
        )
        .scalars()
        .all()
    )
    source_reviews = (
        (
            await db.execute(
                select(Review).where(Review.store_id == source.id)
            )
        )
        .scalars()
        .all()
    )
    moved_reviews = 0
    dropped = 0
    for rv in source_reviews:
        if rv.user_id in target_reviewers:
            await db.delete(rv)
            dropped += 1
        else:
            rv.store_id = target.id
            moved_reviews += 1

    moved_flags = (
        await db.execute(
            update(Flag).where(Flag.store_id == source.id).values(store_id=target.id)
        )
    ).rowcount
    moved_qr = (
        await db.execute(
            update(StoreQrToken)
            .where(StoreQrToken.store_id == source.id)
            .values(store_id=target.id)
        )
    ).rowcount
    moved_claims = (
        await db.execute(
            update(StoreClaim)
            .where(StoreClaim.store_id == source.id)
            .values(store_id=target.id)
        )
    ).rowcount
    moved_posts = (
        await db.execute(
            update(Post).where(Post.store_id == source.id).values(store_id=target.id)
        )
    ).rowcount

    await db.flush()

    # target 집계 재계산
    target_stat = await db.get(StoreStat, target.id)
    if target_stat is None:
        target_stat = StoreStat(store_id=target.id)
        db.add(target_stat)
    target_stat.gold_flag_count = await _count(
        db, Flag.store_id == target.id, Flag.type == FlagType.GOLD
    )
    target_stat.silver_flag_count = await _count(
        db, Flag.store_id == target.id, Flag.type == FlagType.SILVER
    )
    target_stat.conqueror_count = (
        await db.execute(
            select(func.count(func.distinct(Flag.user_id))).where(
                Flag.store_id == target.id
            )
        )
    ).scalar_one()
    await review_service.recompute_store_rating(db, target.id)

    # 소유자 승계: target 이 비어 있고 source 가 인증 소유자면 이어받는다
    owner_inherited = False
    if target.owner_id is None and source.owner_id is not None:
        target.owner_id = source.owner_id
        target.is_verified_owner = True
        owner_inherited = True

    # source 폐점 처리 + 집계 0
    source.status = StoreStatus.CLOSED
    source.owner_id = None
    source.is_verified_owner = False
    source_stat = await db.get(StoreStat, source.id)
    if source_stat is not None:
        source_stat.gold_flag_count = 0
        source_stat.silver_flag_count = 0
        source_stat.conqueror_count = 0
        source_stat.average_rating = None

    await db.flush()

    return MergeResult(
        target_id=target.id,
        source_id=source.id,
        moved_flags=moved_flags,
        moved_reviews=moved_reviews,
        dropped_duplicate_reviews=dropped,
        moved_posts=moved_posts,
        moved_claims=moved_claims,
        moved_qr_tokens=moved_qr,
        owner_inherited=owner_inherited,
    )
