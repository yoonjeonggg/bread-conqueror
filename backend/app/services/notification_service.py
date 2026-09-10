"""인앱 알림 생성 헬퍼 (로드맵 6단계).

flag_service 와 같은 규칙: 이 모듈은 커밋하지 않는다. 세션에 Notification 을
추가만 하고, 알림을 유발한 원래 액션과 같은 트랜잭션에서 함께 커밋된다.
따라서 원래 액션이 롤백되면 알림도 남지 않는다.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.models.notification import Notification


async def create(
    db: AsyncSession,
    *,
    recipient_id: int,
    type: NotificationType,
    message: str,
    actor_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
) -> Notification | None:
    """알림을 세션에 추가한다. 본인이 유발한 알림은 만들지 않는다."""
    if actor_id is not None and actor_id == recipient_id:
        return None
    row = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=type,
        message=message[:255],
        target_type=target_type,
        target_id=target_id,
    )
    db.add(row)
    return row


async def unread_count(db: AsyncSession, user_id: int) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
            )
        )
    ).scalar_one()
