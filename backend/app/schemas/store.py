from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StoreCreatedSource, StoreStatus


class StoreStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gold_flag_count: int
    silver_flag_count: int
    conqueror_count: int
    average_rating: Decimal | None


class StoreBase(BaseModel):
    name: str = Field(max_length=100)
    address: str = Field(max_length=255)
    region_sido: str | None = Field(default=None, max_length=50)
    lat: Decimal = Field(ge=-90, le=90)
    lng: Decimal = Field(ge=-180, le=180)
    category: str | None = Field(default=None, max_length=50)
    thumbnail_url: str | None = Field(default=None, max_length=500)


class StoreCreate(StoreBase):
    pass


class StoreOut(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_source: StoreCreatedSource
    is_verified_owner: bool
    owner_id: int | None = None
    status: StoreStatus
    stat: StoreStatOut | None = None


class StoreListItem(StoreOut):
    distance_m: float | None = None
    conquered_by_me: bool = False


class NearbyDuplicateWarning(BaseModel):
    message: str
    stores: list[StoreOut]


class StoreSearchResult(BaseModel):
    total: int
    items: list[StoreListItem]


class StoreFilters(BaseModel):
    regions: list[str]
    categories: list[str]
