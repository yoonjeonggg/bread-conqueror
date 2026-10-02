import base64
import binascii
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, DbSession
from app.core.redis import redis_client
from app.models.enums import EvidenceType, FlagType, NotificationType
from app.models.flag import Flag
from app.models.store import Store
from app.models.store_qr_token import StoreQrToken
from app.models.user import User, UserStat
from app.schemas.claim import QrConquerRequest
from app.schemas.flag import ConquestResponse, FlagCreate, FlagOut, MyFlagOut
from app.services import (
    flag_service,
    notification_service,
    ranking_service,
    store_service,
)
from app.utils.exif import extract

router = APIRouter(prefix="/flags", tags=["flags"])

# ~10MB image once base64-encoded (+ data-URL prefix). Anything bigger is not a
# phone photo; refuse it before decoding/parsing rather than after.
MAX_EXIF_IMAGE_B64 = 14_000_000


async def _finish_conquest(
    db: AsyncSession,
    user: User,
    store: Store,
    result: flag_service.ConquestResult,
) -> ConquestResponse:
    """Shared tail of GPS and QR conquests: tier-up notice, commit, ranking."""
    if result.tier_changed:
        await notification_service.create(
            db,
            recipient_id=user.id,
            type=NotificationType.TIER_UP,
            message=f"축하합니다! 티어가 Lv.{result.new_tier_level}(으)로 상승했습니다.",
            target_type="USER",
            target_id=user.id,
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


@router.post("", response_model=ConquestResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    payload: FlagCreate, db: DbSession, user: CurrentUser
) -> ConquestResponse:
    store = await store_service.get_open_store(db, payload.store_id, with_stat=True)

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
    return await _finish_conquest(db, user, store, result)


@router.post("/qr", response_model=ConquestResponse, status_code=status.HTTP_201_CREATED)
async def conquer_by_qr(
    payload: QrConquerRequest, db: DbSession, user: CurrentUser
) -> ConquestResponse:
    """매장에 부착된 QR 토큰으로 골드 깃발을 발급한다 (F-CONQ / 로드맵 5단계)."""
    token = (
        await db.execute(
            select(StoreQrToken).where(StoreQrToken.token == payload.token)
        )
    ).scalar_one_or_none()
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="유효하지 않은 QR입니다."
        )
    gone = HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="만료되었거나 사용 한도에 도달한 QR입니다.",
    )
    if not token.is_active(datetime.utcnow()):
        raise gone

    # consume one use atomically: a read-then-increment lets two simultaneous
    # scans both pass the max_uses check. If the flag below fails, the request
    # rolls back and the use is returned.
    consumed = await db.execute(
        update(StoreQrToken)
        .where(
            StoreQrToken.id == token.id,
            or_(
                StoreQrToken.max_uses.is_(None),
                StoreQrToken.use_count < StoreQrToken.max_uses,
            ),
        )
        .values(use_count=StoreQrToken.use_count + 1)
        .execution_options(synchronize_session=False)
    )
    if consumed.rowcount != 1:
        raise gone

    store = await store_service.get_open_store(db, token.store_id, with_stat=True)

    result = await flag_service.create_flag(
        db,
        user=user,
        store=store,
        flag_type=FlagType.GOLD,
        lat=None,
        lng=None,
        evidence_type=EvidenceType.QR,
        evidence_image_url=None,
        visited_at=None,
        via_qr=True,
    )
    if store.owner_id is not None:
        await notification_service.create(
            db,
            recipient_id=store.owner_id,
            actor_id=user.id,
            type=NotificationType.QR_CONQUEST,
            message=f"{user.nickname}님이 QR로 '{store.name}'을(를) 정복했습니다.",
            target_type="STORE",
            target_id=store.id,
        )
    return await _finish_conquest(db, user, store, result)


@router.get("/me", response_model=list[MyFlagOut])
async def my_flags(
    db: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[MyFlagOut]:
    # newest first, paged by id cursor — heavy conquerors have hundreds of flags
    stmt = (
        select(Flag, Store.name)
        .join(Store, Store.id == Flag.store_id)
        .where(Flag.user_id == user.id)
        .order_by(Flag.id.desc())
        .limit(limit)
    )
    if before_id is not None:
        stmt = stmt.where(Flag.id < before_id)
    rows = (await db.execute(stmt)).all()
    return [
        MyFlagOut.model_validate({**flag.__dict__, "store_name": name})
        for flag, name in rows
    ]


class ExifPreviewRequest(BaseModel):
    image_base64: str = Field(min_length=1, max_length=MAX_EXIF_IMAGE_B64)


class ExifPreviewResponse(BaseModel):
    captured_at: str | None
    lat: float | None
    lng: float | None
    has_gps: bool
    trust: str


@router.post("/exif-preview", response_model=ExifPreviewResponse)
async def exif_preview(
    payload: ExifPreviewRequest, user: CurrentUser
) -> ExifPreviewResponse:
    """F-CONQ-05 — 실버 깃발 사진의 EXIF를 미리 읽어 신뢰도를 가늠한다."""
    raw = payload.image_base64.split(",", 1)[-1]
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미지 디코딩 실패"
        ) from exc

    info = extract(data)
    if info.captured_at and info.has_gps:
        trust = "HIGH"
    elif info.captured_at or info.has_gps:
        trust = "MEDIUM"
    else:
        trust = "LOW"

    return ExifPreviewResponse(
        captured_at=info.captured_at.isoformat() if info.captured_at else None,
        lat=info.lat,
        lng=info.lng,
        has_gps=info.has_gps,
        trust=trust,
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
