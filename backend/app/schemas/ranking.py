from pydantic import BaseModel


class RankingEntry(BaseModel):
    rank: int
    user_id: int
    nickname: str
    tier_level: int
    exp: int


class RankingResponse(BaseModel):
    scope: str
    region_sido: str | None = None
    entries: list[RankingEntry]
    my_rank: int | None = None
