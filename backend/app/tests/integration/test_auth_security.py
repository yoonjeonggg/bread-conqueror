"""Auth hardening: login throttling, account status on login/refresh, token
type/claim checks, and claim URL scheme validation."""

from decimal import Decimal

import jwt
from sqlalchemy import update

from app.core.config import settings
from app.core.security import create_refresh_token
from app.models.enums import StoreCreatedSource, StoreStatus, UserStatus
from app.models.store import Store, StoreStat
from app.models.user import User

PASSWORD = "password123"


async def _register(client, n: int = 1) -> tuple[int, str]:
    email = f"sec{n}@test.dev"
    res = await client.post(
        "/api/v1/auth/register",
        json={"nickname": f"sec{n}", "email": email, "password": PASSWORD},
    )
    assert res.status_code == 201
    return res.json()["id"], email


async def _login(client, email: str, password: str = PASSWORD):
    return await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


async def test_login_locks_out_after_repeated_failures(client):
    _, email = await _register(client)
    for _ in range(settings.login_max_attempts):
        assert (await _login(client, email, "wrong-password")).status_code == 401

    res = await _login(client, email)  # even the right password is refused now
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) > 0


async def test_unknown_email_failures_are_throttled_too(client):
    for _ in range(settings.login_max_attempts):
        assert (await _login(client, "nobody@test.dev")).status_code == 401
    assert (await _login(client, "nobody@test.dev")).status_code == 429


async def test_successful_login_resets_failure_count(client):
    _, email = await _register(client)
    for _ in range(settings.login_max_attempts - 1):
        await _login(client, email, "wrong-password")
    assert (await _login(client, email)).status_code == 200
    # counter starts over, so another near-limit run still isn't locked out
    for _ in range(settings.login_max_attempts - 1):
        await _login(client, email, "wrong-password")
    assert (await _login(client, email)).status_code == 200


async def test_suspended_user_cannot_login_or_refresh(client, db_session):
    user_id, email = await _register(client)
    refresh_token = (await _login(client, email)).json()["refresh_token"]

    await db_session.execute(
        update(User).where(User.id == user_id).values(status=UserStatus.SUSPENDED)
    )
    await db_session.commit()

    assert (await _login(client, email)).status_code == 403
    res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert res.status_code == 403


async def test_refresh_token_is_not_accepted_as_access_token(client):
    user_id, _ = await _register(client)
    res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {create_refresh_token(user_id)}"},
    )
    assert res.status_code == 401


async def test_token_without_expiry_is_rejected(client):
    user_id, _ = await _register(client)
    forever = jwt.encode(
        {"sub": str(user_id), "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    res = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {forever}"}
    )
    assert res.status_code == 401


async def test_claim_rejects_non_http_license_url(client, db_session):
    store = Store(
        name="빵집",
        address="서울",
        lat=Decimal("37.5"),
        lng=Decimal("127.0"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    store.stat = StoreStat()
    db_session.add(store)
    await db_session.commit()

    _, email = await _register(client)
    token = (await _login(client, email)).json()["access_token"]
    res = await client.post(
        f"/api/v1/stores/{store.id}/claims",
        json={
            "business_license_image_url": "javascript:alert(document.cookie)",
            "contact_phone": "010-1234-5678",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


async def test_store_search_treats_wildcards_literally(client, db_session):
    for name in ("100%빵집", "일반빵집"):
        store = Store(
            name=name,
            address="서울",
            lat=Decimal("37.5"),
            lng=Decimal("127.0"),
            created_source=StoreCreatedSource.AUTO_COLLECTED,
            status=StoreStatus.ACTIVE,
        )
        store.stat = StoreStat()
        db_session.add(store)
    await db_session.commit()

    res = await client.get("/api/v1/stores/search", params={"q": "%"})
    assert [s["name"] for s in res.json()["items"]] == ["100%빵집"]
