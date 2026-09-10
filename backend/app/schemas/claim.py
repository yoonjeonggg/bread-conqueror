from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ClaimStatus


class ClaimCreate(BaseModel):
    business_license_image_url: str = Field(min_length=1, max_length=500)
    contact_phone: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-]+$")


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    user_id: int
    status: ClaimStatus
    review_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class MyClaimOut(ClaimOut):
    store_name: str


class AdminClaimOut(ClaimOut):
    store_name: str
    user_nickname: str
    business_license_image_url: str
    contact_phone: str


class ClaimReviewRequest(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class QrTokenCreate(BaseModel):
    label: str | None = Field(default=None, max_length=50)
    max_uses: int | None = Field(default=None, ge=1, le=100000)
    expires_in_hours: int | None = Field(default=None, ge=1, le=8760)


class QrTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    token: str
    label: str | None
    max_uses: int | None
    use_count: int
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    active: bool


class QrConquerRequest(BaseModel):
    token: str = Field(min_length=1, max_length=64)
