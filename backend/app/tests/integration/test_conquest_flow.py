"""End-to-end: register -> add store -> gold conquest -> stats + cooldown."""

from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.enums import StoreCreatedSource, StoreStatus
from app.models.store import Store, StoreStat

STORE_LAT, STORE_LNG = 37.5642, 126.9770


@pytest_asyncio.fixture
async def seeded_store(db_session) -> Store:
    store = Store(
        name="테스트 베이커리",
        address="서울 중구",
        region_sido="서울",
        lat=Decimal(str(STORE_LAT)),
        lng=Decimal(str(STORE_LNG)),
        category="베이커리",
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    store.stat = StoreStat()
    db_session.add(store)
    await db_session.commit()
    return store


async def _auth(client) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "nickname": "정복자1",
            "email": "c1@test.dev",
            "password": "password123",
        },
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "c1@test.dev", "password": "password123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_gold_conquest_updates_stats_and_enforces_cooldown(
    client, seeded_store
) -> None:
    headers = await _auth(client)

    far = await client.post(
        "/api/v1/flags",
        headers=headers,
        json={
            "store_id": seeded_store.id,
            "type": "GOLD",
            "lat": 37.6000,
            "lng": 126.9770,
        },
    )
    assert far.status_code == 400

    ok = await client.post(
        "/api/v1/flags",
        headers=headers,
        json={
            "store_id": seeded_store.id,
            "type": "GOLD",
            "lat": STORE_LAT,
            "lng": STORE_LNG,
        },
    )
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["exp_granted"] == 100
    assert body["flag"]["type"] == "GOLD"

    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert me["stat"]["exp"] == 100
    assert me["stat"]["gold_flag_count"] == 1
    assert me["stat"]["conquered_store_count"] == 1

    again = await client.post(
        "/api/v1/flags",
        headers=headers,
        json={
            "store_id": seeded_store.id,
            "type": "GOLD",
            "lat": STORE_LAT,
            "lng": STORE_LNG,
        },
    )
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_silver_flag_grants_half_exp(client, seeded_store) -> None:
    headers = await _auth(client)
    r = await client.post(
        "/api/v1/flags",
        headers=headers,
        json={"store_id": seeded_store.id, "type": "SILVER"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["exp_granted"] == 50
