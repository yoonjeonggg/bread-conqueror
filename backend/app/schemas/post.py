from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ContentStatus


class PostCreate(BaseModel):
    title: str = Field(max_length=100)
    content: str = Field(min_length=1)
    store_id: int | None = None


class AuthorBadge(BaseModel):
    user_id: int
    nickname: str
    tier_level: int
    flag_count: int


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    store_id: int | None
    like_count: int
    status: ContentStatus
    created_at: datetime
    author_tier_snapshot: int
    author_flag_count_snapshot: int


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
