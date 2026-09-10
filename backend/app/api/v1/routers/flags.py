import base64
import binascii
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, DbSession
from app.core.redis import redis_client
from app.models.enums import EvidenceType, FlagType, NotificationType, StoreStatus
from app.models.flag import Flag
from app.models.store import Store
from app.models.store_qr_token import StoreQrToken
from app.models.user import UserStat
from app.schemas.claim import QrConquerRequest
from app.schemas.flag import ConquestResponse, FlagCreate, FlagOut
from app.services import flag_service, notification_service, ranking_service
from app.utils.exif import extract


def _tier_up_message(level: int) -> str:
    return f"축하합니다! 티어가 Lv.{level}(으)로 상승했습니다."

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
    if result.tier_changed:
        await notification_service.create(
            db,
            recipient_id=user.id,
            type=NotificationType.TIER_UP,
            message=_tier_up_message(result.new_tier_level),
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
    if not token.is_active(datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="만료되었거나 사용 한도에 도달한 QR입니다.",
        )

    store = (
        await db.execute(
            select(Store)
            .options(selectinload(Store.stat))
            .where(Store.id == token.store_id)
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
        flag_type=FlagType.GOLD,
        lat=None,
        lng=None,
        evidence_type=EvidenceType.QR,
        evidence_image_url=None,
        visited_at=None,
        via_qr=True,
    )
    token.use_count += 1

    if result.tier_changed:
        await notification_service.create(
            db,
            recipient_id=user.id,
            type=NotificationType.TIER_UP,
            message=_tier_up_message(result.new_tier_level),
            target_type="USER",
            target_id=user.id,
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


class ExifPreviewRequest(BaseModel):
    image_base64: str = Field(min_length=1)


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
