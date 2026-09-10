"""팔로우 (F-RANK-03 친구 랭킹의 기반) + 신고 (F-CONQ-10, F-BOARD-03)."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import CurrentUser, DbSession, OptionalUser
from app.models.enums import NotificationType, ReportTargetType
from app.models.post import Post
from app.models.social import Follow, Report
from app.models.user import User, UserStat
from app.schemas.social import FollowCounts, FollowUser, ReportCreate, ReportOut
from app.services import notification_service

router = APIRouter(tags=["social"])


@router.post("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow(user_id: int, db: DbSession, me: CurrentUser) -> None:
    if user_id == me.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신은 팔로우할 수 없습니다.",
        )
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    db.add(Follow(follower_id=me.id, followee_id=user_id))
    await notification_service.create(
        db,
        recipient_id=user_id,
        actor_id=me.id,
        type=NotificationType.FOLLOW,
        message=f"{me.nickname}님이 회원님을 팔로우했습니다.",
        target_type="USER",
        target_id=me.id,
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # already following — idempotent (알림도 함께 롤백)


@router.delete("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow(user_id: int, db: DbSession, me: CurrentUser) -> None:
    row = (
        await db.execute(
            select(Follow).where(
                Follow.follower_id == me.id, Follow.followee_id == user_id
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.commit()


@router.get("/users/{user_id}/follow-counts", response_model=FollowCounts)
async def follow_counts(
    user_id: int, db: DbSession, me: OptionalUser
) -> FollowCounts:
    followers = (
        await db.execute(
            select(func.count()).select_from(Follow).where(Follow.followee_id == user_id)
        )
    ).scalar_one()
    following = (
        await db.execute(
            select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
        )
    ).scalar_one()
    is_following = False
    if me is not None:
        is_following = (
            await db.execute(
                select(Follow.id).where(
                    Follow.follower_id == me.id, Follow.followee_id == user_id
                )
            )
        ).scalar_one_or_none() is not None
    return FollowCounts(
        followers=followers, following=following, is_following=is_following
    )


@router.get("/users/{user_id}/following", response_model=list[FollowUser])
async def following_list(user_id: int, db: DbSession) -> list[FollowUser]:
    rows = (
        await db.execute(
            select(User.id, User.nickname, UserStat.tier_level)
            .join(Follow, Follow.followee_id == User.id)
            .join(UserStat, UserStat.user_id == User.id, isouter=True)
            .where(Follow.follower_id == user_id)
        )
    ).all()
    return [
        FollowUser(user_id=r.id, nickname=r.nickname, tier_level=r.tier_level or 1)
        for r in rows
    ]


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreate, db: DbSession, me: CurrentUser
) -> Report:
    report = Report(
        reporter_id=me.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
    )
    db.add(report)

    if payload.target_type is ReportTargetType.POST:
        post = await db.get(Post, payload.target_id)
        if post is not None:
            post.report_count += 1

    await db.commit()
    await db.refresh(report)
    return report
