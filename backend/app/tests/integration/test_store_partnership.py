"""제휴 매장 관리 (F-ADMIN-06) — 목록 조회/등록/해제 + 감사 로그 + 알림."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import StoreCreatedSource, StoreStatus, UserRole
from app.models.notification import Notification
from app.models.policy import AdminActionLog
from app.models.store import Store, StoreStat
from app.models.user import User, UserStat


async def _register(client, email: str) -> User:
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": email.split("@")[0], "email": email, "password": "password123"},
    )
    return email


async def _admin(client, db_session, email: str) -> dict[str, str]:
    await _register(client, email)
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
async def owner(client, db_session):
    email = "owner@t.dev"
    await _register(client, email)
    return (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()


@pytest_asyncio.fixture
async def store(db_session, owner):
    s = Store(
        name="정복 베이커리",
        address="서울 어딘가",
        region_sido="서울",
        lat=Decimal("37.5"),
        lng=Decimal("127.0"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
        owner_id=owner.id,
        is_verified_owner=True,
    )
    s.stat = StoreStat()
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.mark.asyncio
async def test_grant_and_revoke_partnership(client, db_session, store, owner):
    h = await _admin(client, db_session, "padmin@t.dev")

    r = await client.post(
        f"/api/v1/admin/stores/{store.id}/partnership",
        headers=h,
        json={"note": "1호 제휴점"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_partner"] is True
    assert body["partnered_at"] is not None

    # 중복 등록은 409
    dup = await client.post(
        f"/api/v1/admin/stores/{store.id}/partnership", headers=h, json={}
    )
    assert dup.status_code == 409

    notif = (
        await db_session.execute(
            select(Notification).where(Notification.recipient_id == owner.id)
        )
    ).scalar_one()
    assert notif.type.value == "PARTNERSHIP_GRANTED"

    listed = await client.get("/api/v1/admin/stores/partners", headers=h)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == store.id

    revoke = await client.request(
        "DELETE",
        f"/api/v1/admin/stores/{store.id}/partnership",
        headers=h,
        json={"note": "계약 종료"},
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["is_partner"] is False
    assert revoke.json()["partnered_at"] is None

    # 이미 해제된 상태에서 재해제는 409
    redo = await client.request(
        "DELETE", f"/api/v1/admin/stores/{store.id}/partnership", headers=h, json={}
    )
    assert redo.status_code == 409

    logs = (
        await db_session.execute(
            select(AdminActionLog).where(AdminActionLog.target_type == "STORE")
        )
    ).scalars().all()
    action_types = {row.action_type for row in logs}
    assert "STORE_PARTNERSHIP_GRANT" in action_types
    assert "STORE_PARTNERSHIP_REVOKE" in action_types


@pytest.mark.asyncio
async def test_partnership_requires_admin(client, store):
    r = await client.post(f"/api/v1/admin/stores/{store.id}/partnership", json={})
    assert r.status_code == 401
