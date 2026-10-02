"""Profile page data: paged flag history with store names, tier progress."""

from decimal import Decimal

from sqlalchemy import select

from app.models.enums import EvidenceType, FlagType, StoreCreatedSource, StoreStatus
from app.models.flag import Flag
from app.models.store import Store, StoreStat
from app.models.user import User


async def _auth(client) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": "프로필러", "email": "p1@test.dev", "password": "password123"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "p1@test.dev", "password": "password123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_flags(db_session, count: int) -> None:
    user = (
        await db_session.execute(select(User).where(User.email == "p1@test.dev"))
    ).scalar_one()
    store = Store(
        name="크루아상 하우스",
        address="서울 마포구",
        region_sido="서울",
        lat=Decimal("37.55"),
        lng=Decimal("126.92"),
        category="베이커리",
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    store.stat = StoreStat()
    db_session.add(store)
    await db_session.flush()
    for _ in range(count):
        db_session.add(
            Flag(
                user_id=user.id,
                store_id=store.id,
                type=FlagType.SILVER,
                evidence_type=EvidenceType.NONE,
                exp_granted=30,
            )
        )
    await db_session.commit()


async def test_my_flags_include_store_name_and_page_by_cursor(client, db_session):
    headers = await _auth(client)
    await _seed_flags(db_session, 5)

    first = await client.get("/api/v1/flags/me?limit=3", headers=headers)
    assert first.status_code == 200, first.text
    page1 = first.json()
    assert len(page1) == 3
    assert page1[0]["store_name"] == "크루아상 하우스"
    ids = [f["id"] for f in page1]
    assert ids == sorted(ids, reverse=True)

    rest = await client.get(
        f"/api/v1/flags/me?limit=3&before_id={ids[-1]}", headers=headers
    )
    page2 = rest.json()
    assert len(page2) == 2
    assert all(f["id"] < ids[-1] for f in page2)


async def test_my_profile_reports_next_tier(client):
    headers = await _auth(client)
    me = (await client.get("/api/v1/users/me", headers=headers)).json()

    assert me["stat"]["tier_level"] == 1
    assert me["tier_min_exp"] == 0
    assert me["next_tier_name"]
    assert me["next_tier_exp"] > 0
