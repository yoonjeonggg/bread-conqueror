"""매장 소유권 신청(Claim) + 정복용 QR 토큰 (로드맵 5단계).

- 사용자: 매장 소유권 신청, 내 신청 현황 조회
- 인증된 소유자: 매장 QR 토큰 발급 / 목록 / 폐기
- 관리자 승인·반려는 `routers/admin.py` 에 있다.
"""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.enums import ClaimStatus
from app.models.store import Store
from app.models.store_claim import StoreClaim
from app.models.store_qr_token import StoreQrToken
from app.schemas.claim import (
    ClaimCreate,
    ClaimOut,
    MyClaimOut,
    QrTokenCreate,
    QrTokenOut,
)

router = APIRouter(tags=["claims"])


def _token_out(row: StoreQrToken, now: datetime | None = None) -> QrTokenOut:
    now = now or datetime.utcnow()
    return QrTokenOut.model_validate(
        {**row.__dict__, "active": row.is_active(now)}
    )


async def _owned_store(db: DbSession, store_id: int, user: CurrentUser) -> Store:
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="매장을 찾을 수 없습니다."
        )
    if store.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="인증된 매장 소유자만 사용할 수 있습니다.",
        )
    return store


# --- 소유권 신청 -------------------------------------------------------


@router.post(
    "/stores/{store_id}/claims",
    response_model=ClaimOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_claim(
    store_id: int, payload: ClaimCreate, db: DbSession, user: CurrentUser
) -> StoreClaim:
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="매장을 찾을 수 없습니다."
        )
    if store.owner_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 인증된 소유자가 있는 매장입니다.",
        )

    dupe = (
        await db.execute(
            select(StoreClaim.id).where(
                StoreClaim.store_id == store_id,
                StoreClaim.user_id == user.id,
                StoreClaim.status == ClaimStatus.PENDING,
            )
        )
    ).scalar_one_or_none()
    if dupe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 심사 대기 중인 신청이 있습니다.",
        )

    claim = StoreClaim(
        store_id=store_id,
        user_id=user.id,
        business_license_image_url=payload.business_license_image_url,
        contact_phone=payload.contact_phone,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


@router.get("/me/claims", response_model=list[MyClaimOut])
async def my_claims(db: DbSession, user: CurrentUser) -> list[MyClaimOut]:
    rows = (
        await db.execute(
            select(StoreClaim, Store.name)
            .join(Store, Store.id == StoreClaim.store_id)
            .where(StoreClaim.user_id == user.id)
            .order_by(StoreClaim.created_at.desc())
        )
    ).all()
    return [
        MyClaimOut.model_validate({**claim.__dict__, "store_name": name})
        for claim, name in rows
    ]


# --- QR 토큰 (소유자 전용) --------------------------------------------


@router.post(
    "/stores/{store_id}/qr-tokens",
    response_model=QrTokenOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_qr_token(
    store_id: int, payload: QrTokenCreate, db: DbSession, user: CurrentUser
) -> QrTokenOut:
    await _owned_store(db, store_id, user)
    expires_at = (
        datetime.utcnow() + timedelta(hours=payload.expires_in_hours)
        if payload.expires_in_hours is not None
        else None
    )
    row = StoreQrToken(
        store_id=store_id,
        token=secrets.token_urlsafe(24),
        created_by=user.id,
        label=payload.label,
        max_uses=payload.max_uses,
        expires_at=expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _token_out(row)


@router.get("/stores/{store_id}/qr-tokens", response_model=list[QrTokenOut])
async def list_qr_tokens(
    store_id: int, db: DbSession, user: CurrentUser
) -> list[QrTokenOut]:
    await _owned_store(db, store_id, user)
    now = datetime.utcnow()
    rows = (
        (
            await db.execute(
                select(StoreQrToken)
                .where(StoreQrToken.store_id == store_id)
                .order_by(StoreQrToken.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_token_out(r, now) for r in rows]


@router.delete(
    "/stores/{store_id}/qr-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_qr_token(
    store_id: int, token_id: int, db: DbSession, user: CurrentUser
) -> None:
    await _owned_store(db, store_id, user)
    row = await db.get(StoreQrToken, token_id)
    if row is None or row.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if row.revoked_at is None:
        row.revoked_at = datetime.utcnow()
        await db.commit()
