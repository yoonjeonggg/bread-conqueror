from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: Decimal = Field(ge=0, le=5, multiple_of=Decimal("0.5"))
    content: str | None = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    user_id: int
    rating: Decimal
    content: str | None
    created_at: datetime


class ReviewWithAuthor(ReviewOut):
    author_nickname: str
    author_tier_level: int
