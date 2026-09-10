"""리뷰 집계 + 팔로우/친구 랭킹 + 신고/관리자 처리."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import StoreCreatedSource, StoreStatus, UserRole
from app.models.store import Store, StoreStat
from app.models.user import User


@pytest_asyncio.fixture
async def store(db_session) -> Store:
    s = Store(
        name="리뷰 베이커리",
        address="서울 종로구",
        region_sido="서울",
        lat=Decimal("37.5720"),
        lng=Decimal("126.9794"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    db_session.add(s)
    await db_session.commit()
    return s


async def _register(client, nickname: str, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": nickname, "email": email, "password": "password123"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_review_upsert_updates_aggregates(client, store, db_session):
    h1 = await _register(client, "리뷰어A", "ra@test.dev")
    h2 = await _register(client, "리뷰어B", "rb@test.dev")

    r = await client.post(
        f"/api/v1/stores/{store.id}/reviews",
        headers=h1,
        json={"rating": 4.0, "content": "촉촉함"},
    )
    assert r.status_code == 201
    await client.post(
        f"/api/v1/stores/{store.id}/reviews",
        headers=h2,
        json={"rating": 5.0},
    )

    detail = (await client.get(f"/api/v1/stores/{store.id}")).json()
    assert float(detail["stat"]["average_rating"]) == 4.5

    # upsert: same user updates instead of adding a second row
    await client.post(
        f"/api/v1/stores/{store.id}/reviews", headers=h1, json={"rating": 2.0}
    )
    detail = (await client.get(f"/api/v1/stores/{store.id}")).json()
    assert float(detail["stat"]["average_rating"]) == 3.5

    listing = (await client.get(f"/api/v1/stores/{store.id}/reviews")).json()
    assert len(listing) == 2

    me = (await client.get("/api/v1/users/me", headers=h1)).json()
    assert me["stat"]["review_count"] == 1


@pytest.mark.asyncio
async def test_follow_and_friends_ranking(client, store):
    h1 = await _register(client, "팔로워", "f1@test.dev")
    await _register(client, "대상", "f2@test.dev")

    # user ids: 1 and 2 (sequential)
    r = await client.post("/api/v1/users/2/follow", headers=h1)
    assert r.status_code == 204

    counts = (await client.get("/api/v1/users/2/follow-counts", headers=h1)).json()
    assert counts["followers"] == 1
    assert counts["is_following"] is True

    # give the followee some exp via a silver flag
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "f2@test.dev", "password": "password123"},
    )
    h2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.post(
        "/api/v1/flags",
        headers=h2,
        json={"store_id": store.id, "type": "SILVER"},
    )

    fr = (await client.get("/api/v1/rankings/friends", headers=h1)).json()
    assert fr["scope"] == "friends"
    assert {e["user_id"] for e in fr["entries"]} == {1, 2}

    await client.delete("/api/v1/users/2/follow", headers=h1)
    counts = (await client.get("/api/v1/users/2/follow-counts", headers=h1)).json()
    assert counts["followers"] == 0


@pytest.mark.asyncio
async def test_report_flows_to_admin_and_resolves(client, store, db_session):
    reporter = await _register(client, "신고자", "rep@test.dev")
    await _register(client, "관리자후보", "adm@test.dev")

    admin = (
        await db_session.execute(select(User).where(User.email == "adm@test.dev"))
    ).scalar_one()
    admin.role = UserRole.ADMIN
    await db_session.commit()

    admin_h = {
        "Authorization": "Bearer "
        + (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "adm@test.dev", "password": "password123"},
            )
        ).json()["access_token"]
    }

    rep = await client.post(
        "/api/v1/reports",
        headers=reporter,
        json={"target_type": "FLAG", "target_id": 999, "reason": "허위 인증 같음"},
    )
    assert rep.status_code == 201
    report_id = rep.json()["id"]

    queue = (await client.get("/api/v1/admin/reports", headers=admin_h)).json()
    assert any(r["id"] == report_id for r in queue)

    res = await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=admin_h,
        json={"status": "REVIEWED", "note": "확인함"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REVIEWED"

    queue = (await client.get("/api/v1/admin/reports", headers=admin_h)).json()
    assert not any(r["id"] == report_id for r in queue)


@pytest.mark.asyncio
async def test_admin_adjust_exp_moves_tier(client, store, db_session):
    await _register(client, "조정대상", "adj@test.dev")
    await _register(client, "관리자2", "adm2@test.dev")

    admin = (
        await db_session.execute(select(User).where(User.email == "adm2@test.dev"))
    ).scalar_one()
    admin.role = UserRole.ADMIN
    await db_session.commit()

    admin_h = {
        "Authorization": "Bearer "
        + (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "adm2@test.dev", "password": "password123"},
            )
        ).json()["access_token"]
    }

    res = await client.post(
        "/api/v1/admin/users/1/adjust-exp",
        headers=admin_h,
        json={"exp_delta": 500, "reason": "이벤트 보상"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["exp"] == 500
    assert body["tier_level"] == 2
    assert body["tier_changed"] is True

    # non-admin blocked
    blocked = await client.post(
        "/api/v1/admin/users/1/adjust-exp",
        headers={"Authorization": "Bearer bogus"},
        json={"exp_delta": 1, "reason": "x"},
    )
    assert blocked.status_code == 401
