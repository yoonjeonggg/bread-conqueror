"""중복 매장 병합 (F-ADMIN-04) — 참조 이관 + 집계 재계산 + source 폐점."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import (
    EvidenceType,
    FlagType,
    StoreCreatedSource,
    StoreStatus,
    UserRole,
)
from app.models.flag import Flag
from app.models.review import Review
from app.models.store import Store, StoreStat
from app.models.user import User, UserStat


def _store(name: str, lat: float) -> Store:
    s = Store(
        name=name,
        address="서울 어딘가",
        region_sido="서울",
        lat=Decimal(str(lat)),
        lng=Decimal("127.0"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    return s


def _flag(user_id: int, store_id: int, ftype: FlagType) -> Flag:
    return Flag(
        user_id=user_id,
        store_id=store_id,
        type=ftype,
        evidence_type=EvidenceType.NONE,
        exp_granted=100 if ftype is FlagType.GOLD else 50,
    )


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
async def scene(db_session):
    users = [
        User(nickname=f"su{i}", email=f"su{i}@t.dev", password_hash="x")
        for i in range(1, 4)
    ]
    for u in users:
        u.stat = UserStat()
    src = _store("빵집 (중복)", 37.50)
    tgt = _store("빵집 본점", 37.51)
    db_session.add_all([*users, src, tgt])
    await db_session.flush()

    db_session.add_all(
        [
            _flag(users[0].id, src.id, FlagType.GOLD),
            _flag(users[1].id, src.id, FlagType.SILVER),
            _flag(users[2].id, tgt.id, FlagType.GOLD),
            # 두 매장 모두 리뷰한 u1 → 병합 시 source 리뷰 폐기
            Review(user_id=users[0].id, store_id=src.id, rating=Decimal("3.0")),
            Review(user_id=users[0].id, store_id=tgt.id, rating=Decimal("5.0")),
            # source 에만 리뷰한 u2 → 이관
            Review(user_id=users[1].id, store_id=src.id, rating=Decimal("4.0")),
        ]
    )
    await db_session.commit()
    return {"src": src.id, "tgt": tgt.id}


@pytest.mark.asyncio
async def test_merge_moves_refs_and_recomputes(client, scene, db_session):
    h = await _admin(client, db_session, "ra@t.dev")

    r = await client.post(
        f"/api/v1/admin/stores/{scene['tgt']}/merge",
        headers=h,
        json={"source_id": scene["src"], "note": "같은 가게"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["moved_flags"] == 2
    assert body["moved_reviews"] == 1
    assert body["dropped_duplicate_reviews"] == 1

    tgt = (await client.get(f"/api/v1/stores/{scene['tgt']}")).json()
    assert tgt["stat"]["gold_flag_count"] == 2
    assert tgt["stat"]["silver_flag_count"] == 1
    assert tgt["stat"]["conqueror_count"] == 3  # u1, u2, u3
    assert float(tgt["stat"]["average_rating"]) == 4.5  # u1(tgt)=5.0, u2=4.0

    src = (await client.get(f"/api/v1/stores/{scene['src']}")).json()
    assert src["status"] == "CLOSED"
    assert src["stat"]["gold_flag_count"] == 0

    src_flags = (
        (await db_session.execute(select(Flag).where(Flag.store_id == scene["src"])))
        .scalars()
        .all()
    )
    assert src_flags == []


@pytest.mark.asyncio
async def test_merge_guards(client, scene, db_session):
    h = await _admin(client, db_session, "a2@t.dev")

    same = await client.post(
        f"/api/v1/admin/stores/{scene['tgt']}/merge",
        headers=h,
        json={"source_id": scene["tgt"]},
    )
    assert same.status_code == 400

    missing = await client.post(
        f"/api/v1/admin/stores/{scene['tgt']}/merge",
        headers=h,
        json={"source_id": 999999},
    )
    assert missing.status_code == 404

    ok = await client.post(
        f"/api/v1/admin/stores/{scene['tgt']}/merge",
        headers=h,
        json={"source_id": scene["src"]},
    )
    assert ok.status_code == 200
    again = await client.post(
        f"/api/v1/admin/stores/{scene['tgt']}/merge",
        headers=h,
        json={"source_id": scene["src"]},
    )
    assert again.status_code == 409

    blocked = await client.post(
        f"/api/v1/admin/stores/{scene['tgt']}/merge",
        json={"source_id": scene["src"]},
    )
    assert blocked.status_code == 401
