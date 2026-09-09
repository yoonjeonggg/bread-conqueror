from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EvidenceType, FlagStatus, FlagType


class FlagCreate(BaseModel):
    store_id: int
    type: FlagType
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    evidence_type: EvidenceType = EvidenceType.NONE
    evidence_image_url: str | None = Field(default=None, max_length=500)
    visited_at: datetime | None = None

    @model_validator(mode="after")
    def _validate(self) -> "FlagCreate":
        if self.type is FlagType.GOLD and (self.lat is None or self.lng is None):
            raise ValueError("골드 깃발은 lat/lng 가 필요합니다.")
        return self


class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    user_id: int
    type: FlagType
    evidence_type: EvidenceType
    evidence_image_url: str | None
    exp_granted: int
    is_flagged: bool
    status: FlagStatus
    upgraded_from_silver: bool
    lat_at_conquest: Decimal | None
    lng_at_conquest: Decimal | None
    visited_at: datetime | None
    created_at: datetime


class ConquestResponse(BaseModel):
    flag: FlagOut
    exp_granted: int
    tier_changed: bool
    new_tier_level: int
    upgraded_from_silver: bool
    is_flagged: bool
    abuse_reasons: list[str] = []
