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
    national_rank: int | None = None
