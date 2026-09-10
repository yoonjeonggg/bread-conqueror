from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import contains_eager, selectinload

from app.core.dependencies import CurrentUser, DbSession, OptionalUser
from app.models.enums import StoreCreatedSource, StoreStatus
from app.models.flag import Flag
from app.models.store import Store, StoreStat
from app.schemas.store import (
    StoreCreate,
    StoreFilters,
    StoreListItem,
    StoreOut,
    StoreSearchResult,
)
from app.services.geo_service import bounding_box, haversine_m

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreListItem])
async def list_nearby(
    db: DbSession,
    user: OptionalUser,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=50, le=20000)] = 2000,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[StoreListItem]:
    min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_m)
    rows = (
        (
            await db.execute(
                select(Store)
                .options(selectinload(Store.stat))
                .where(
                    Store.status == StoreStatus.ACTIVE,
                    Store.lat.between(min_lat, max_lat),
                    Store.lng.between(min_lng, max_lng),
                )
                .limit(limit * 3)
            )
        )
        .scalars()
        .all()
    )

    my_store_ids: set[int] = set()
    if user is not None and rows:
        my_store_ids = set(
            (
                await db.execute(
                    select(Flag.store_id.distinct()).where(
                        Flag.user_id == user.id,
                        Flag.store_id.in_([s.id for s in rows]),
                    )
                )
            )
            .scalars()
            .all()
        )

    items: list[StoreListItem] = []
    for store in rows:
        distance = haversine_m(lat, lng, float(store.lat), float(store.lng))
        if distance > radius_m:
            continue
        item = StoreListItem.model_validate(store)
        item.distance_m = round(distance, 1)
        item.conquered_by_me = store.id in my_store_ids
        items.append(item)

    items.sort(key=lambda s: s.distance_m or 0)
    return items[:limit]


@router.get("/search", response_model=StoreSearchResult)
async def search_stores(
    db: DbSession,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    region_sido: Annotated[str | None, Query(max_length=50)] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    verified_only: bool = False,
    sort: Literal["popular", "rating", "recent"] = "popular",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> StoreSearchResult:
    """F-SEARCH — 위치와 무관한 키워드/필터 검색."""
    conds = [Store.status == StoreStatus.ACTIVE]
    if q and q.strip():
        like = f"%{q.strip()}%"
        conds.append(or_(Store.name.ilike(like), Store.address.ilike(like)))
    if region_sido:
        conds.append(Store.region_sido == region_sido)
    if category:
        conds.append(Store.category == category)
    if verified_only:
        conds.append(Store.is_verified_owner.is_(True))

    total = (
        await db.execute(
            select(func.count()).select_from(Store).where(*conds)
        )
    ).scalar_one()

    stmt = (
        select(Store)
        .outerjoin(StoreStat, StoreStat.store_id == Store.id)
        .options(contains_eager(Store.stat))
        .where(*conds)
    )
    if sort == "popular":
        stmt = stmt.order_by(StoreStat.conqueror_count.desc(), Store.id.desc())
    elif sort == "rating":
        stmt = stmt.order_by(StoreStat.average_rating.desc(), Store.id.desc())
    else:
        stmt = stmt.order_by(Store.id.desc())
    stmt = stmt.limit(limit).offset(offset)

    rows = (await db.execute(stmt)).scalars().all()

    mine: set[int] = set()
    if user is not None and rows:
        mine = set(
            (
                await db.execute(
                    select(Flag.store_id.distinct()).where(
                        Flag.user_id == user.id,
                        Flag.store_id.in_([s.id for s in rows]),
                    )
                )
            )
            .scalars()
            .all()
        )

    items: list[StoreListItem] = []
    for store in rows:
        item = StoreListItem.model_validate(store)
        item.conquered_by_me = store.id in mine
        items.append(item)
    return StoreSearchResult(total=total, items=items)


@router.get("/filters", response_model=StoreFilters)
async def store_filters(db: DbSession) -> StoreFilters:
    """검색 드롭다운용 지역/카테고리 목록."""

    async def distinct(column) -> list[str]:
        return list(
            (
                await db.execute(
                    select(column)
                    .distinct()
                    .where(column.isnot(None), Store.status == StoreStatus.ACTIVE)
                    .order_by(column)
                )
            )
            .scalars()
            .all()
        )

    return StoreFilters(
        regions=await distinct(Store.region_sido),
        categories=await distinct(Store.category),
    )


@router.get("/{store_id}", response_model=StoreOut)
async def get_store(store_id: int, db: DbSession) -> Store:
    store = (
        await db.execute(
            select(Store)
            .options(selectinload(Store.stat))
            .where(Store.id == store_id)
        )
    ).scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="매장을 찾을 수 없습니다."
        )
    return store


@router.post("", response_model=StoreOut, status_code=status.HTTP_201_CREATED)
async def create_store(
    payload: StoreCreate, db: DbSession, user: CurrentUser
) -> Store:
    """F-MAP-04 / F-STORE-02 — user-submitted store with a dupe check."""
    min_lat, max_lat, min_lng, max_lng = bounding_box(
        float(payload.lat), float(payload.lng), 100
    )
    nearby = (
        (
            await db.execute(
                select(Store).where(
                    Store.lat.between(min_lat, max_lat),
                    Store.lng.between(min_lng, max_lng),
                )
            )
        )
        .scalars()
        .all()
    )
    for existing in nearby:
        d = haversine_m(
            float(payload.lat),
            float(payload.lng),
            float(existing.lat),
            float(existing.lng),
        )
        if d <= 30:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"반경 30m 내에 이미 '{existing.name}' 매장이 있습니다.",
            )

    store = Store(
        **payload.model_dump(),
        created_source=StoreCreatedSource.USER_ADDED,
        status=StoreStatus.PENDING_REVIEW,
    )
    store.stat = StoreStat()
    db.add(store)
    await db.commit()
    await db.refresh(store, attribute_names=["stat"])
    return store
