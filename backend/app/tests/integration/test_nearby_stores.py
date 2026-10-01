"""주변 매장 조회 (F-MAP-01/02) — 거리순 정렬이 limit 보다 먼저 적용되는지."""

from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.enums import StoreCreatedSource, StoreStatus
from app.models.store import Store, StoreStat

CENTER_LAT, CENTER_LNG = 37.5663, 126.9779


def _store(name: str, lat: float, lng: float) -> Store:
    s = Store(
        name=name,
        address="서울 어딘가",
        region_sido="서울",
        lat=Decimal(str(lat)),
        lng=Decimal(str(lng)),
        category="베이커리",
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    return s


@pytest_asyncio.fixture
async def crowded(db_session):
    # 먼 매장을 먼저 대량으로 넣고(반경 안, ~2.5km 남쪽) 가장 가까운 매장을 맨 나중에 넣는다
    # — DB 가 삽입 순서나 (lat 인덱스) 순서로 돌려주면 정렬 전 limit 에 잘려 가까운 매장이 누락된다.
    far = [_store(f"먼 빵집 {i}", CENTER_LAT - 0.022, CENTER_LNG + i * 0.00001) for i in range(40)]
    near = _store("바로 앞 빵집", CENTER_LAT + 0.0005, CENTER_LNG)
    db_session.add_all(far)
    await db_session.flush()
    db_session.add(near)
    await db_session.commit()
    return near.id


@pytest.mark.asyncio
async def test_nearby_returns_closest_first_even_when_truncated(client, crowded):
    r = await client.get(
        f"/api/v1/stores?lat={CENTER_LAT}&lng={CENTER_LNG}&radius_m=3000&limit=5"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 5
    assert items[0]["id"] == crowded
    distances = [s["distance_m"] for s in items]
    assert distances == sorted(distances)


@pytest.mark.asyncio
async def test_nearby_excludes_bbox_corners_outside_radius(client, db_session):
    # 바운딩 박스 모서리(반경 밖)는 제외
    db_session.add_all(
        [_store("반경 안", CENTER_LAT + 0.005, CENTER_LNG),
         _store("모서리", CENTER_LAT + 0.0085, CENTER_LNG + 0.0107)]
    )
    await db_session.commit()
    r = await client.get(f"/api/v1/stores?lat={CENTER_LAT}&lng={CENTER_LNG}&radius_m=1000")
    assert [s["name"] for s in r.json()] == ["반경 안"]
