from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ContentStatus, ReportStatus, ReportTargetType, UserStatus


class SuspendRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=255)


class AdjustExpRequest(BaseModel):
    exp_delta: int = Field(ge=-100000, le=100000)
    reason: str = Field(min_length=2, max_length=255)


class ModerateRequest(BaseModel):
    status: ContentStatus
    reason: str | None = Field(default=None, max_length=255)


class ResolveReportRequest(BaseModel):
    status: ReportStatus = ReportStatus.REVIEWED
    note: str | None = Field(default=None, max_length=255)


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    email: str
    status: UserStatus
    role: str


class AdminReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    target_type: ReportTargetType
    target_id: int
    reason: str
    status: ReportStatus
    created_at: datetime


class AdjustResultOut(BaseModel):
    user_id: int
    exp: int
    tier_level: int
    tier_changed: bool


class StoreMergeRequest(BaseModel):
    source_id: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class StoreMergeResult(BaseModel):
    target_id: int
    source_id: int
    moved_flags: int
    moved_reviews: int
    dropped_duplicate_reviews: int
    moved_posts: int
    moved_claims: int
    moved_qr_tokens: int
    owner_inherited: bool


class BulkUploadRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=1_000_000)
    dry_run: bool = False


class BulkUploadRowResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line: int
    name: str
    status: str
    detail: str | None = None
    store_id: int | None = None


class BulkUploadResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dry_run: bool
    total: int
    created: int
    skipped_duplicate: int
    failed: int
    rows: list[BulkUploadRowResult]


class DashboardOut(BaseModel):
    total_users: int
    total_stores: int
    total_flags: int
    gold_ratio: float
    flags_this_week: int
    pending_review: int
    pending_reports: int
    pending_claims: int
    suspended_users: int
    average_store_rating: Decimal | None
