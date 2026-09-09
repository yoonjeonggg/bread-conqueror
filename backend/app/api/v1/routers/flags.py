from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DbSession
from app.core.redis import redis_client
from app.models.enums import StoreStatus
from app.models.flag import Flag
from app.models.store import Store
from app.models.user import UserStat
from app.schemas.flag import ConquestResponse, FlagCreate, FlagOut
from app.services import flag_service, ranking_service

router = APIRouter(prefix="/flags", tags=["flags"])


@router.post("", response_model=ConquestResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    payload: FlagCreate, db: DbSession, user: CurrentUser
) -> ConquestResponse:
    store = (
        await db.execute(
            select(Store)
            .options(selectinload(Store.stat))
            .where(Store.id == payload.store_id)
        )
    ).scalar_one_or_none()
    if store is None or store.status == StoreStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="매장을 찾을 수 없습니다."
        )

    result = await flag_service.create_flag(
        db,
        user=user,
        store=store,
        flag_type=payload.type,
        lat=payload.lat,
        lng=payload.lng,
        evidence_type=payload.evidence_type,
        evidence_image_url=payload.evidence_image_url,
        visited_at=payload.visited_at,
    )
    await db.commit()
    await db.refresh(result.flag)

    user_stat = await db.get(UserStat, user.id)
    if user_stat is not None:
        await ranking_service.set_score(
            redis_client, user.id, user_stat.exp, store.region_sido
        )

    return ConquestResponse(
        flag=FlagOut.model_validate(result.flag),
        exp_granted=result.exp_granted,
        tier_changed=result.tier_changed,
        new_tier_level=result.new_tier_level,
        upgraded_from_silver=result.upgraded_from_silver,
        is_flagged=result.is_flagged,
        abuse_reasons=result.abuse_reasons,
    )


@router.get("/me", response_model=list[FlagOut])
async def my_flags(db: DbSession, user: CurrentUser) -> list[Flag]:
    return list(
        (
            await db.execute(
                select(Flag)
                .where(Flag.user_id == user.id)
                .order_by(Flag.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@router.get("/store/{store_id}", response_model=list[FlagOut])
async def store_flags(store_id: int, db: DbSession) -> list[Flag]:
    return list(
        (
            await db.execute(
                select(Flag)
                .where(Flag.store_id == store_id)
                .order_by(Flag.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
