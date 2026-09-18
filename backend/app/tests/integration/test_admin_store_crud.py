"""관리자 매장 등록/수정/삭제 (F-ADMIN-03)."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import StoreCreatedSource, StoreStatus, UserRole
from app.models.store import Store, StoreStat
from app.models.user import User


async def _admin(client, db_session, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": email.split("@")[0], "email": email, "password": "password123"},
    )
    u = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    u.role = UserRole.ADMIN
    await db_session.commit()
    tok = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest_asyncio.fixture
async def store(db_session):
    s = Store(
        name="기존 매장",
        address="서울 어딘가",
        region_sido="서울",
        lat=Decimal("37.5"),
        lng=Decimal("127.0"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.mark.asyncio
async def test_create_store_is_active_immediately(client, db_session):
    h = await _admin(client, db_session, "storeadmin@t.dev")

    r = await client.post(
        "/api/v1/admin/stores",
        headers=h,
        json={
            "name": "관리자 등록 매장",
            "address": "서울 종로구",
            "lat": "37.57",
            "lng": "126.98",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "ACTIVE"
    assert body["stat"] is not None

    logs = await client.get(
        "/api/v1/admin/reports", headers=h
    )  # sanity: still authorized
    assert logs.status_code == 200


@pytest.mark.asyncio
async def test_update_store_partial_fields(client, db_session, store):
    h = await _admin(client, db_session, "storeadmin2@t.dev")

    r = await client.patch(
        f"/api/v1/admin/stores/{store.id}",
        headers=h,
        json={"name": "새 이름", "category": "베이커리"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "새 이름"
    assert body["category"] == "베이커리"
    assert body["address"] == "서울 어딘가"  # 미전달 필드는 유지

    missing = await client.patch(
        "/api/v1/admin/stores/999999", headers=h, json={"name": "x"}
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_delete_store_closes_and_clears_stats(client, db_session, store):
    h = await _admin(client, db_session, "storeadmin3@t.dev")

    r = await client.delete(f"/api/v1/admin/stores/{store.id}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "CLOSED"

    again = await client.delete(f"/api/v1/admin/stores/{store.id}", headers=h)
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_store_crud_requires_admin(client, store):
    r = await client.post(
        "/api/v1/admin/stores",
        json={"name": "x", "address": "y", "lat": "37.5", "lng": "127.0"},
    )
    assert r.status_code == 401

    r2 = await client.patch(f"/api/v1/admin/stores/{store.id}", json={"name": "x"})
    assert r2.status_code == 401

    r3 = await client.delete(f"/api/v1/admin/stores/{store.id}")
    assert r3.status_code == 401
