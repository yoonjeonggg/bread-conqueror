from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.review import Review
from app.models.store import Store
from app.models.user import User, UserStat
from app.schemas.review import ReviewCreate, ReviewOut, ReviewWithAuthor
from app.services import review_service

router = APIRouter(tags=["reviews"])


@router.get("/stores/{store_id}/reviews", response_model=list[ReviewWithAuthor])
async def list_reviews(store_id: int, db: DbSession) -> list[ReviewWithAuthor]:
    rows = (
        await db.execute(
            select(Review, User.nickname, UserStat.tier_level)
            .join(User, User.id == Review.user_id)
            .join(UserStat, UserStat.user_id == Review.user_id, isouter=True)
            .where(Review.store_id == store_id)
            .order_by(Review.created_at.desc())
        )
    ).all()
    return [
        ReviewWithAuthor(
            id=r.id,
            store_id=r.store_id,
            user_id=r.user_id,
            rating=r.rating,
            content=r.content,
            created_at=r.created_at,
            author_nickname=nickname,
            author_tier_level=tier_level or 1,
        )
        for r, nickname, tier_level in rows
    ]


@router.post(
    "/stores/{store_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_review(
    store_id: int, payload: ReviewCreate, db: DbSession, user: CurrentUser
) -> Review:
    if await db.get(Store, store_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="매장을 찾을 수 없습니다."
        )

    review = (
        await db.execute(
            select(Review).where(
                Review.store_id == store_id, Review.user_id == user.id
            )
        )
    ).scalar_one_or_none()

    if review is None:
        review = Review(
            store_id=store_id,
            user_id=user.id,
            rating=payload.rating,
            content=payload.content,
        )
        db.add(review)
    else:
        review.rating = payload.rating
        review.content = payload.content

    await db.flush()
    await review_service.recompute_store_rating(db, store_id)
    await review_service.recompute_user_review_count(db, user.id)
    await db.commit()
    await db.refresh(review)
    return review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: int, db: DbSession, user: CurrentUser) -> None:
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if review.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="본인 리뷰만 삭제할 수 있습니다."
        )

    store_id = review.store_id
    await db.delete(review)
    await db.flush()
    await review_service.recompute_store_rating(db, store_id)
    await review_service.recompute_user_review_count(db, user.id)
    await db.commit()
