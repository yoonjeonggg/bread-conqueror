from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, BigIntPK
from app.models.enums import NotificationType


class Notification(Base):
    """인앱 알림 (로드맵 6단계).

    `message` 는 생성 시점에 렌더한 문구를 그대로 저장한다 (역정규화). 조회할 때
    조인을 최소화하고, 원본 리소스가 나중에 바뀌거나 삭제돼도 알림은 남는다.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "idx_notifications_recipient",
            "recipient_id",
            "is_read",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    target_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
