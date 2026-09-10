"""인앱 알림 (로드맵 6단계) — 팔로우·댓글·좋아요·Claim 심사·티어 상승."""

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
        name="알림 베이커리",
        address="서울 마포구",
        region_sido="서울",
        lat=Decimal("37.5551"),
        lng=Decimal("126.9368"),
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


async def _unread(client, headers) -> int:
    r = await client.get("/api/v1/notifications/unread-count", headers=headers)
    return r.json()["count"]


@pytest.mark.asyncio
async def test_follow_notifies_followee_and_marks_read(client):
    a = await _register(client, "팔로워A", "na@test.dev")  # user 1
    b = await _register(client, "대상B", "nb@test.dev")  # user 2

    assert (await client.post("/api/v1/users/2/follow", headers=a)).status_code == 204

    assert await _unread(client, b) == 1
    assert await _unread(client, a) == 0  # 본인은 알림 없음

    items = (await client.get("/api/v1/notifications", headers=b)).json()
    assert len(items) == 1
    assert items[0]["type"] == "FOLLOW"
    assert items[0]["actor_nickname"] == "팔로워A"
    assert items[0]["target_type"] == "USER"
    assert items[0]["is_read"] is False

    # 재팔로우(멱등)는 알림을 중복 생성하지 않는다
    await client.post("/api/v1/users/2/follow", headers=a)
    assert await _unread(client, b) == 1

    assert (
        await client.post("/api/v1/notifications/read", headers=b, json={})
    ).status_code == 204
    assert await _unread(client, b) == 0


@pytest.mark.asyncio
async def test_comment_and_like_notify_post_author_not_self(client):
    author = await _register(client, "글쓴이", "author@test.dev")  # 1
    other = await _register(client, "댓글러", "other@test.dev")  # 2

    pid = (
        await client.post(
            "/api/v1/posts",
            headers=author,
            json={"title": "성수동 크루아상 성지", "content": "겉바속촉"},
        )
    ).json()["id"]

    # 본인이 자기 글에 댓글/좋아요 → 알림 없음
    await client.post(
        f"/api/v1/posts/{pid}/comments", headers=author, json={"content": "자답"}
    )
    assert await _unread(client, author) == 0

    # 남이 댓글 + 좋아요 → 2건
    await client.post(
        f"/api/v1/posts/{pid}/comments", headers=other, json={"content": "동의합니다"}
    )
    await client.post(f"/api/v1/posts/{pid}/like", headers=other)
    assert await _unread(client, author) == 2

    types = {
        n["type"]
        for n in (await client.get("/api/v1/notifications", headers=author)).json()
    }
    assert types == {"POST_COMMENT", "POST_LIKE"}

    # only_unread 필터 + 단건 읽음
    items = (
        await client.get(
            "/api/v1/notifications?only_unread=true", headers=author
        )
    ).json()
    first_id = items[0]["id"]
    await client.post(
        "/api/v1/notifications/read", headers=author, json={"ids": [first_id]}
    )
    assert await _unread(client, author) == 1


@pytest.mark.asyncio
async def test_claim_decision_and_tier_up_notifications(client, store, db_session):
    applicant = await _register(client, "사장님", "owner@test.dev")  # 1
    await _register(client, "관리자", "adm@test.dev")  # 2

    admin_row = (
        await db_session.execute(select(User).where(User.email == "adm@test.dev"))
    ).scalar_one()
    admin_row.role = UserRole.ADMIN
    await db_session.commit()
    admin = {
        "Authorization": "Bearer "
        + (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "adm@test.dev", "password": "password123"},
            )
        ).json()["access_token"]
    }

    claim_id = (
        await client.post(
            f"/api/v1/stores/{store.id}/claims",
            headers=applicant,
            json={
                "business_license_image_url": "https://img/x.jpg",
                "contact_phone": "01012345678",
            },
        )
    ).json()["id"]

    await client.post(
        f"/api/v1/admin/claims/{claim_id}/approve",
        headers=admin,
        json={"note": "확인"},
    )
    items = (await client.get("/api/v1/notifications", headers=applicant)).json()
    assert [n["type"] for n in items] == ["CLAIM_APPROVED"]
    assert "승인" in items[0]["message"]

    # 관리자 경험치 조정 → 티어 상승 알림
    await client.post(
        "/api/v1/admin/users/1/adjust-exp",
        headers=admin,
        json={"exp_delta": 400, "reason": "이벤트"},
    )
    types = [
        n["type"]
        for n in (
            await client.get("/api/v1/notifications", headers=applicant)
        ).json()
    ]
    assert types == ["TIER_UP", "CLAIM_APPROVED"]  # 최신순
