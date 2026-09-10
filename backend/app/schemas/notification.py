from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    actor_id: int | None
    actor_nickname: str | None = None
    target_type: str | None
    target_id: int | None
    message: str
    is_read: bool
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int


class MarkReadRequest(BaseModel):
    ids: list[int] | None = None  # None → 전체 읽음 처리
