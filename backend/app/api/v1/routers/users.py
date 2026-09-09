from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DbSession
from app.core.redis import redis_client
from app.models.user import User, UserStat
from app.schemas.user import ProfileOut, UserStatOut
from app.services import ranking_service, tier_service

router = APIRouter(prefix="/users", tags=["users"])


async def _profile(db: DbSession, user: User) -> ProfileOut:
    stat = await db.get(UserStat, user.id) or UserStat(user_id=user.id)
    rank = await ranking_service.get_rank(redis_client, user.id)
    return ProfileOut(
        id=user.id,
        nickname=user.nickname,
        email=user.email,
        profile_image_url=user.profile_image_url,
        role=user.role,
        stat=UserStatOut.model_validate(stat),
        tier_name=await tier_service.tier_name(db, stat.tier_level),
        national_rank=rank,
    )


@router.get("/me", response_model=ProfileOut)
async def my_profile(db: DbSession, user: CurrentUser) -> ProfileOut:
    return await _profile(db, user)


@router.get("/{user_id}", response_model=ProfileOut)
async def public_profile(user_id: int, db: DbSession) -> ProfileOut:
    user = (
        await db.execute(
            select(User).options(selectinload(User.stat)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )
    return await _profile(db, user)
