"""매장 소유권 신청(Claim) 승인 → QR 토큰 발급 → QR 정복 (로드맵 5단계)."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import StoreCreatedSource, StoreStatus, UserRole
from app.models.store import Store, StoreStat
from app.models.user import User

STORE_LAT, STORE_LNG = 37.5449, 127.0561


@pytest_asyncio.fixture
async def store(db_session) -> Store:
    s = Store(
        name="정복 베이커리",
        address="서울 성동구",
        region_sido="서울",
        lat=Decimal(str(STORE_LAT)),
        lng=Decimal(str(STORE_LNG)),
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


async def _promote_admin(client, db_session, email: str) -> dict[str, str]:
    admin = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    admin.role = UserRole.ADMIN
    await db_session.commit()
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_claim_approval_then_qr_conquest(client, store, db_session):
    owner = await _register(client, "사장님", "owner@test.dev")
    await _register(client, "관리자", "adm@test.dev")
    admin = await _promote_admin(client, db_session, "adm@test.dev")

    # 신청
    r = await client.post(
        f"/api/v1/stores/{store.id}/claims",
        headers=owner,
        json={
            "business_license_image_url": "https://img.test/license.jpg",
            "contact_phone": "010-1234-5678",
        },
    )
    assert r.status_code == 201, r.text
    claim_id = r.json()["id"]
    assert r.json()["status"] == "PENDING"

    # 중복 신청 차단
    dup = await client.post(
        f"/api/v1/stores/{store.id}/claims",
        headers=owner,
        json={
            "business_license_image_url": "https://img.test/license.jpg",
            "contact_phone": "010-1234-5678",
        },
    )
    assert dup.status_code == 409

    # 내 신청 현황
    mine = (await client.get("/api/v1/me/claims", headers=owner)).json()
    assert mine[0]["store_name"] == "정복 베이커리"

    # 관리자 큐 → 승인
    queue = (await client.get("/api/v1/admin/claims", headers=admin)).json()
    assert any(c["id"] == claim_id for c in queue)

    ap = await client.post(
        f"/api/v1/admin/claims/{claim_id}/approve",
        headers=admin,
        json={"note": "서류 확인"},
    )
    assert ap.status_code == 200, ap.text
    assert ap.json()["status"] == "APPROVED"

    detail = (await client.get(f"/api/v1/stores/{store.id}")).json()
    assert detail["is_verified_owner"] is True

    # QR 토큰 발급 (소유자)
    tok = await client.post(
        f"/api/v1/stores/{store.id}/qr-tokens",
        headers=owner,
        json={"label": "카운터", "max_uses": 2},
    )
    assert tok.status_code == 201, tok.text
    token = tok.json()["token"]
    assert tok.json()["active"] is True

    # 손님이 QR 스캔 → 골드 깃발 (GPS 없이)
    visitor = await _register(client, "손님", "guest@test.dev")
    conq = await client.post(
        "/api/v1/flags/qr", headers=visitor, json={"token": token}
    )
    assert conq.status_code == 201, conq.text
    body = conq.json()
    assert body["flag"]["type"] == "GOLD"
    assert body["flag"]["evidence_type"] == "QR"
    assert body["exp_granted"] == 100

    # 같은 매장 재정복은 쿨다운
    again = await client.post(
        "/api/v1/flags/qr", headers=visitor, json={"token": token}
    )
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_qr_token_guardrails(client, store, db_session):
    owner = await _register(client, "사장2", "owner2@test.dev")
    outsider = await _register(client, "외부인", "out@test.dev")

    # 인증 전에는 QR 발급 불가
    denied = await client.post(
        f"/api/v1/stores/{store.id}/qr-tokens", headers=owner, json={}
    )
    assert denied.status_code == 403

    # 소유자 직접 연결 (승인 플로우 축약). owner 가 먼저 가입 → user id 1.
    s = await db_session.get(Store, store.id)
    s.owner_id = 1
    s.is_verified_owner = True
    await db_session.commit()

    tok = await client.post(
        f"/api/v1/stores/{store.id}/qr-tokens", headers=owner, json={}
    )
    token_id = tok.json()["id"]
    token = tok.json()["token"]

    # 비소유자는 목록 조회 불가
    assert (
        await client.get(f"/api/v1/stores/{store.id}/qr-tokens", headers=outsider)
    ).status_code == 403

    # 폐기 후에는 정복 불가
    rv = await client.delete(
        f"/api/v1/stores/{store.id}/qr-tokens/{token_id}", headers=owner
    )
    assert rv.status_code == 204

    gone = await client.post(
        "/api/v1/flags/qr", headers=outsider, json={"token": token}
    )
    assert gone.status_code == 410

    bad = await client.post(
        "/api/v1/flags/qr", headers=outsider, json={"token": "nope"}
    )
    assert bad.status_code == 404


@pytest.mark.asyncio
async def test_cannot_claim_owned_store(client, store, db_session):
    await _register(client, "선점자", "first@test.dev")
    later = await _register(client, "후발주자", "second@test.dev")

    s = await db_session.get(Store, store.id)
    s.owner_id = 1  # "선점자" 가 먼저 가입
    await db_session.commit()

    r = await client.post(
        f"/api/v1/stores/{store.id}/claims",
        headers=later,
        json={
            "business_license_image_url": "https://img.test/x.jpg",
            "contact_phone": "01099998888",
        },
    )
    assert r.status_code == 409
