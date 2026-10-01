"""코드 리뷰에서 발견한 버그/보안 이슈 회귀 테스트."""

import base64
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from app.models.enums import ContentStatus, StoreCreatedSource, StoreStatus
from app.models.flag import Flag
from app.models.post import Post
from app.models.store import Store, StoreStat
from app.models.store_qr_token import StoreQrToken
from app.models.user import UserStat

A_LAT, A_LNG = 37.5642, 126.9770
B_LAT, B_LNG = 37.5000, 127.0000


def _post(author_id: int, title: str, **kw) -> Post:
    return Post(
        user_id=author_id,
        title=title,
        content="x",
        author_tier_snapshot=1,
        author_flag_count_snapshot=0,
        **kw,
    )


def _store(name: str, lat: float, lng: float) -> Store:
    s = Store(
        name=name,
        address="서울",
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
async def stores(db_session):
    a, b = _store("A 빵집", A_LAT, A_LNG), _store("B 빵집", B_LAT, B_LNG)
    db_session.add_all([a, b])
    await db_session.commit()
    return a.id, b.id


async def _signup(client, n: int) -> tuple[int, dict[str, str]]:
    email = f"u{n}@test.dev"
    r = await client.post(
        "/api/v1/auth/register",
        json={"nickname": f"유저{n}", "email": email, "password": "password123"},
    )
    uid = r.json()["id"]
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return uid, {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _age_all_flags(db_session, hours: int = 72) -> None:
    """쿨다운을 지나게 하려고 기존 깃발 시각을 과거로 민다."""
    await db_session.execute(
        update(Flag).values(created_at=datetime.utcnow() - timedelta(hours=hours))
    )
    await db_session.commit()


# ── 공개 프로필 이메일 노출 ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_public_profile_does_not_expose_email(client):
    uid, headers = await _signup(client, 1)

    public = (await client.get(f"/api/v1/users/{uid}")).json()
    assert public.get("email") is None

    mine = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert mine["email"] == "u1@test.dev"


# ── 실버→골드 업그레이드 중복 적용 ─────────────────────────────────────
@pytest.mark.asyncio
async def test_silver_upgrade_is_applied_only_once(client, db_session, stores):
    a, b = stores
    uid, headers = await _signup(client, 1)

    for sid in (a, b):
        r = await client.post(
            "/api/v1/flags", headers=headers, json={"store_id": sid, "type": "SILVER"}
        )
        assert r.status_code == 201, r.text
    await _age_all_flags(db_session)

    gold = {"store_id": a, "type": "GOLD", "lat": A_LAT, "lng": A_LNG}
    first = await client.post("/api/v1/flags", headers=headers, json=gold)
    assert first.status_code == 201, first.text
    assert first.json()["upgraded_from_silver"] is True
    await _age_all_flags(db_session)

    second = await client.post("/api/v1/flags", headers=headers, json=gold)
    assert second.status_code == 201, second.text
    assert second.json()["upgraded_from_silver"] is False

    db_session.expire_all()
    user_stat = await db_session.get(UserStat, uid)
    # B 매장의 실버는 그대로 남아 있어야 한다
    assert user_stat.silver_flag_count == 1
    assert user_stat.gold_flag_count == 2
    store_a = await db_session.get(StoreStat, a)
    store_b = await db_session.get(StoreStat, b)
    assert store_a.silver_flag_count == 0
    assert store_b.silver_flag_count == 1


# ── QR 사용 한도 경쟁 조건 ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_qr_use_limit_is_enforced_atomically(
    client, db_session, stores, monkeypatch
):
    a, _ = stores
    uid, headers = await _signup(client, 1)
    token = StoreQrToken(
        store_id=a, token="t" * 32, max_uses=1, use_count=1, created_by=uid
    )
    db_session.add(token)
    await db_session.commit()
    token_id = token.id

    # 동시 요청이 둘 다 '아직 여유 있음'을 읽은 상황을 재현: 읽기 검사를 통과시킨다
    monkeypatch.setattr(StoreQrToken, "is_active", lambda self, now: True)

    r = await client.post("/api/v1/flags/qr", headers=headers, json={"token": "t" * 32})
    assert r.status_code == 410

    db_session.expire_all()
    row = (
        await db_session.execute(select(StoreQrToken).where(StoreQrToken.id == token_id))
    ).scalar_one()
    assert row.use_count == 1
    assert (await db_session.execute(select(Flag))).first() is None


# ── EXIF 미리보기 크기 제한 ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_exif_preview_rejects_oversized_payload(client):
    _, headers = await _signup(client, 1)
    huge = base64.b64encode(b"\0" * (11 * 1024 * 1024)).decode()
    r = await client.post(
        "/api/v1/flags/exif-preview", headers=headers, json={"image_base64": huge}
    )
    assert r.status_code == 422


# ── 숨김 글 좋아요/댓글 ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cannot_like_or_comment_hidden_post(client, db_session):
    author_id, _ = await _signup(client, 1)
    _, headers = await _signup(client, 2)
    post = _post(author_id, "숨김", status=ContentStatus.HIDDEN)
    db_session.add(post)
    await db_session.commit()

    assert (
        await client.post(f"/api/v1/posts/{post.id}/like", headers=headers)
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/posts/{post.id}/comments", headers=headers, json={"content": "hi"}
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_like_count_increments_once_per_user(client, db_session):
    author_id, _ = await _signup(client, 1)
    _, headers = await _signup(client, 2)
    post = _post(author_id, "글")
    db_session.add(post)
    await db_session.commit()

    assert (await client.post(f"/api/v1/posts/{post.id}/like", headers=headers)).status_code == 204
    assert (await client.post(f"/api/v1/posts/{post.id}/like", headers=headers)).status_code == 409
    assert (await client.get(f"/api/v1/posts/{post.id}")).json()["like_count"] == 1


# ── 중복 신고 ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_duplicate_report_does_not_inflate_count(client, db_session):
    author_id, _ = await _signup(client, 1)
    _, headers = await _signup(client, 2)
    post = _post(author_id, "글")
    db_session.add(post)
    await db_session.commit()

    post_id = post.id
    body = {"target_type": "POST", "target_id": post_id, "reason": "스팸입니다"}
    assert (await client.post("/api/v1/reports", headers=headers, json=body)).status_code == 201
    assert (await client.post("/api/v1/reports", headers=headers, json=body)).status_code == 409

    db_session.expire_all()
    assert (await db_session.get(Post, post_id)).report_count == 1


# ── 게시판 검색 와일드카드 ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_post_search_treats_wildcards_literally(client, db_session):
    author_id, _ = await _signup(client, 1)
    db_session.add_all(
        [
            _post(author_id, "할인 100%"),
            _post(author_id, "그냥 글"),
        ]
    )
    await db_session.commit()

    r = (await client.get("/api/v1/posts", params={"q": "%"})).json()
    assert [p["title"] for p in r] == ["할인 100%"]
