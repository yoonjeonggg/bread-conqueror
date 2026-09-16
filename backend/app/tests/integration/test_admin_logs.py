"""관리자 활동 감사 로그 (F-ADMIN-11) — 기존 관리자 액션 기록 + 조회/필터."""

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import UserRole
from app.models.user import User, UserStat


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
async def target_user(db_session):
    u = User(nickname="target", email="target@t.dev", password_hash="x")
    u.stat = UserStat()
    db_session.add(u)
    await db_session.commit()
    return u


@pytest.mark.asyncio
async def test_admin_action_creates_log_and_is_queryable(
    client, db_session, target_user
):
    h = await _admin(client, db_session, "logadmin@t.dev")

    r = await client.post(
        f"/api/v1/admin/users/{target_user.id}/suspend",
        headers=h,
        json={"reason": "테스트 정지"},
    )
    assert r.status_code == 200, r.text

    logs = await client.get("/api/v1/admin/logs", headers=h)
    assert logs.status_code == 200, logs.text
    body = logs.json()
    assert body["total"] >= 1
    entry = body["items"][0]
    assert entry["action_type"] == "USER_SUSPEND"
    assert entry["target_type"] == "USER"
    assert entry["target_id"] == target_user.id
    assert entry["detail"] == "테스트 정지"
    assert entry["admin_nickname"] == "logadmin"


@pytest.mark.asyncio
async def test_admin_logs_filter_by_action_type(client, db_session, target_user):
    h = await _admin(client, db_session, "logadmin2@t.dev")

    await client.post(
        f"/api/v1/admin/users/{target_user.id}/suspend",
        headers=h,
        json={"reason": "정지"},
    )
    await client.post(
        f"/api/v1/admin/users/{target_user.id}/reactivate", headers=h
    )

    only_reactivate = await client.get(
        "/api/v1/admin/logs", headers=h, params={"action_type": "USER_REACTIVATE"}
    )
    assert only_reactivate.status_code == 200
    body = only_reactivate.json()
    assert body["total"] == 1
    assert body["items"][0]["action_type"] == "USER_REACTIVATE"

    unauthed = await client.get("/api/v1/admin/logs")
    assert unauthed.status_code == 401
