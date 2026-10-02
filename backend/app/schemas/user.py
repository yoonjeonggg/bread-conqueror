from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class UserStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exp: int
    tier_level: int
    gold_flag_count: int
    silver_flag_count: int
    conquered_store_count: int
    review_count: int
    received_like_count: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    email: str
    profile_image_url: str | None
    role: UserRole


class ProfileOut(UserOut):
    # only filled in for the owner's own profile (/users/me) — never on the
    # public /users/{id} response, which anyone can call without logging in
    email: str | None = None  # type: ignore[assignment]
    stat: UserStatOut
    tier_name: str
    # progress bar on the owner's profile: exp floor of the current tier and the
    # next tier's requirements (null at the top tier)
    tier_min_exp: int = 0
    next_tier_name: str | None = None
    next_tier_exp: int | None = None
    next_tier_gold_ratio: float | None = None
    national_rank: int | None = None
