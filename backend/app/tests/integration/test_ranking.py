"""지역 랭킹 (F-RANK-02) — region_sido 로 필터링되는지 검증.

과거엔 `/rankings/regional` 이 region_sido 를 무시하고 전국 랭킹과 동일한 결과를
반환하던 버그가 있었다. Redis 폴백(DB) 경로와 Redis 경로 둘 다 지역별로 격리
되는지 확인한다.

region_sido 값은 테스트마다 uuid 로 유니크하게 만든다 — 실제 Redis 인스턴스에
붙어서 도는 테스트라 다른 테스트/이전 실행이 남긴 `rank:region:서울` 같은 흔한
지역명 키와 충돌하면 결과가 오염될 수 있기 때문이다.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.enums import EvidenceType, FlagType, StoreCreatedSource, StoreStatus
from app.models.flag import Flag
from app.models.store import Store, StoreStat
from app.models.user import User, UserStat

SEOUL_COORD = (37.5642, 126.9770)
BUSAN_COORD = (35.1796, 129.0756)


def _region() -> str:
    return f"테스트지역-{uuid4().hex[:8]}"


def _store(name: str, region: str, lat: float, lng: float) -> Store:
    s = Store(
        name=name,
        address="어딘가",
        region_sido=region,
        lat=Decimal(str(lat)),
        lng=Decimal(str(lng)),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    return s


@pytest.mark.asyncio
async def test_regional_ranking_db_fallback_filters_by_region(db_session, client):
    region_a = _region()
    region_b = _region()
    store_a = _store("A지역 매장", region_a, *SEOUL_COORD)
    store_b = _store("B지역 매장", region_b, *BUSAN_COORD)
    db_session.add_all([store_a, store_b])
    await db_session.flush()

    user_a = User(nickname="유저A", email="ra@t.dev", password_hash="x")
    user_a.stat = UserStat(exp=300)
    user_b = User(nickname="유저B", email="rb@t.dev", password_hash="x")
    user_b.stat = UserStat(exp=999)  # A 지역보다 높지만 다른 지역이라 안 보여야 함
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    db_session.add(
        Flag(
            user_id=user_a.id,
            store_id=store_a.id,
            type=FlagType.GOLD,
            evidence_type=EvidenceType.REALTIME_GPS,
            exp_granted=300,
        )
    )
    db_session.add(
        Flag(
            user_id=user_b.id,
            store_id=store_b.id,
            type=FlagType.GOLD,
            evidence_type=EvidenceType.REALTIME_GPS,
            exp_granted=999,
        )
    )
    await db_session.commit()

    r = await client.get(
        "/api/v1/rankings/regional", params={"region_sido": region_a}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scope"] == "regional"
    assert body["region_sido"] == region_a
    assert [e["user_id"] for e in body["entries"]] == [user_a.id]

    empty = await client.get(
        "/api/v1/rankings/regional", params={"region_sido": _region()}
    )
    assert empty.json()["entries"] == []


async def _auth(client, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": email.split("@")[0], "email": email, "password": "password123"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_regional_ranking_via_redis_after_conquest(db_session, client):
    region_a = _region()
    region_b = _region()
    store_a = _store("A지역 매장2", region_a, *SEOUL_COORD)
    store_b = _store("B지역 매장2", region_b, *BUSAN_COORD)
    db_session.add_all([store_a, store_b])
    await db_session.commit()

    headers_a = await _auth(client, "rega@t.dev")
    headers_b = await _auth(client, "regb@t.dev")

    conquer_a = await client.post(
        "/api/v1/flags",
        headers=headers_a,
        json={
            "store_id": store_a.id,
            "type": "GOLD",
            "lat": SEOUL_COORD[0],
            "lng": SEOUL_COORD[1],
        },
    )
    assert conquer_a.status_code == 201, conquer_a.text

    conquer_b = await client.post(
        "/api/v1/flags",
        headers=headers_b,
        json={
            "store_id": store_b.id,
            "type": "GOLD",
            "lat": BUSAN_COORD[0],
            "lng": BUSAN_COORD[1],
        },
    )
    assert conquer_b.status_code == 201, conquer_b.text

    r = await client.get(
        "/api/v1/rankings/regional", params={"region_sido": region_a}
    )
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["nickname"] == "rega"
