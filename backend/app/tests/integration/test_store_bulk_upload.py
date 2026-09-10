"""매장 CSV 대량 등록 (F-ADMIN-05) — 검증·중복 스킵·dry-run."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.models.enums import StoreCreatedSource, StoreStatus, UserRole
from app.models.store import Store, StoreStat
from app.models.user import User

HEADER = "name,address,region_sido,lat,lng,category"


@pytest_asyncio.fixture
async def existing_store(db_session) -> Store:
    s = Store(
        name="이미 있는 빵집",
        address="서울 종로구 1",
        region_sido="서울",
        lat=Decimal("37.570000"),
        lng=Decimal("126.980000"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    db_session.add(s)
    await db_session.commit()
    return s


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


async def _count_stores(db_session) -> int:
    return (
        await db_session.execute(select(func.count()).select_from(Store))
    ).scalar_one()


@pytest.mark.asyncio
async def test_bulk_upload_validates_dedups_and_creates(
    client, existing_store, db_session
):
    h = await _admin(client, db_session, "csv@t.dev")
    csv_text = "\n".join(
        [
            HEADER,
            "새 빵집 A,서울 마포구 10,서울,37.5000,126.9000,베이커리",
            "중복 빵집,서울 종로구 1,서울,37.570001,126.980001,베이커리",  # existing_store 와 겹침
            "좌표이상,서울 어딘가,서울,999,126.9,베이커리",  # invalid lat
            "이름없음 대체,서울,서울,37.51,127.01,",  # ok (region 만 있음)
            ",주소만있음,서울,37.52,127.02,",  # name 없음 → failed
        ]
    )

    r = await client.post(
        "/api/v1/admin/stores/bulk-upload",
        headers=h,
        json={"csv_text": csv_text, "dry_run": False},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 5
    assert body["created"] == 2
    assert body["skipped_duplicate"] == 1
    assert body["failed"] == 2

    statuses = {row["line"]: row["status"] for row in body["rows"]}
    assert statuses == {2: "created", 3: "skipped", 4: "failed", 5: "created", 6: "failed"}

    # 실제 생성됨
    assert await _count_stores(db_session) == 3  # existing + 2
    created = (
        await db_session.execute(
            select(Store).where(Store.name == "새 빵집 A")
        )
    ).scalar_one()
    assert created.status == StoreStatus.ACTIVE
    assert created.created_source == StoreCreatedSource.AUTO_COLLECTED


@pytest.mark.asyncio
async def test_dry_run_creates_nothing(client, db_session):
    h = await _admin(client, db_session, "csv2@t.dev")
    before = await _count_stores(db_session)
    csv_text = "\n".join(
        [
            HEADER,
            "드라이런 A,서울 강남구 1,서울,37.50,127.05,베이커리",
            "드라이런 B,서울 강남구 2,서울,37.50001,127.05001,베이커리",  # A 와 겹침
        ]
    )
    r = await client.post(
        "/api/v1/admin/stores/bulk-upload",
        headers=h,
        json={"csv_text": csv_text, "dry_run": True},
    )
    body = r.json()
    assert body["dry_run"] is True
    assert body["created"] == 1
    assert body["skipped_duplicate"] == 1
    assert await _count_stores(db_session) == before


@pytest.mark.asyncio
async def test_bad_header_and_auth(client, db_session):
    h = await _admin(client, db_session, "csv3@t.dev")
    bad = await client.post(
        "/api/v1/admin/stores/bulk-upload",
        headers=h,
        json={"csv_text": "name,address\nfoo,bar", "dry_run": True},
    )
    assert bad.status_code == 400
    assert "lat" in bad.json()["detail"]

    blocked = await client.post(
        "/api/v1/admin/stores/bulk-upload",
        json={"csv_text": f"{HEADER}\nx,y,서울,37.5,127.0,z"},
    )
    assert blocked.status_code == 401
