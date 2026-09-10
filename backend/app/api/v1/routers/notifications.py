"""인앱 알림 조회/읽음 처리 (로드맵 6단계).

알림 생성은 각 액션(팔로우·댓글·좋아요·Claim 심사·티어 상승·QR 정복) 안에서
`services/notification_service.create` 로 이뤄진다.
"""

from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select, update

from app.core.dependencies import CurrentUser, DbSession
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    MarkReadRequest,
    NotificationOut,
    UnreadCountOut,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    db: DbSession,
    me: CurrentUser,
    only_unread: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    before_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[NotificationOut]:
    stmt = (
        select(Notification, User.nickname)
        .join(User, User.id == Notification.actor_id, isouter=True)
        .where(Notification.recipient_id == me.id)
        .order_by(Notification.id.desc())
        .limit(limit)
    )
    if only_unread:
        stmt = stmt.where(Notification.is_read.is_(False))
    if before_id is not None:
        stmt = stmt.where(Notification.id < before_id)

    rows = (await db.execute(stmt)).all()
    return [
        NotificationOut.model_validate(
            {**n.__dict__, "actor_nickname": nickname}
        )
        for n, nickname in rows
    ]


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(db: DbSession, me: CurrentUser) -> UnreadCountOut:
    return UnreadCountOut(count=await notification_service.unread_count(db, me.id))


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    payload: MarkReadRequest, db: DbSession, me: CurrentUser
) -> None:
    stmt = (
        update(Notification)
        .where(
            Notification.recipient_id == me.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    if payload.ids:
        stmt = stmt.where(Notification.id.in_(payload.ids))
    await db.execute(stmt)
    await db.commit()
