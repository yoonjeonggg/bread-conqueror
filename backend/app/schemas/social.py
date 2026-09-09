from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus, ReportTargetType


class FollowCounts(BaseModel):
    followers: int
    following: int
    is_following: bool = False


class FollowUser(BaseModel):
    user_id: int
    nickname: str
    tier_level: int


class ReportCreate(BaseModel):
    target_type: ReportTargetType
    target_id: int
    reason: str = Field(min_length=2, max_length=255)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    target_type: ReportTargetType
    target_id: int
    reason: str
    status: ReportStatus
    created_at: datetime
