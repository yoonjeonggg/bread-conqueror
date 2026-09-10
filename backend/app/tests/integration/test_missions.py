"""주간 미션 (로드맵 8단계) — 진행도 계산 · 보상 1회 수령."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.enums import MissionMetric, StoreCreatedSource, StoreStatus
from app.models.mission import MissionDefinition
from app.models.store import Store, StoreStat


def _store(name: str, sido: str, lat: float) -> Store:
    s = Store(
        name=name,
        address=f"{sido} 어딘가",
        region_sido=sido,
        lat=Decimal(str(lat)),
        lng=Decimal("127.0"),
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
    )
    s.stat = StoreStat()
    return s


@pytest_asyncio.fixture
async def setup(db_session):
    db_session.add_all(
        [
            MissionDefinition(
                code="W_FLAGS_2",
                title="깃발 2개",
                description="이번 주 깃발 2개",
                metric=MissionMetric.TOTAL_FLAGS,
                target=2,
                reward_exp=100,
                sort_order=1,
            ),
            MissionDefinition(
                code="W_REGION_2",
                title="2개 지역",
                description="이번 주 2개 지역 정복",
                metric=MissionMetric.DISTINCT_REGIONS,
                target=2,
                reward_exp=200,
                sort_order=2,
            ),
            _store("서울빵집", "서울", 37.5),
            _store("부산빵집", "부산", 35.1),
        ]
    )
    await db_session.commit()
    rows = (await db_session.execute(select(Store.region_sido, Store.id))).all()
    return dict(rows)


async def _auth(client, nick: str, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": nick, "email": email, "password": "password123"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_weekly_progress_and_single_claim(client, setup):
    h = await _auth(client, "미션러", "mission@test.dev")

    # 처음엔 진행도 0
    wk = (await client.get("/api/v1/missions/weekly", headers=h)).json()
    flags2 = next(m for m in wk["missions"] if m["code"] == "W_FLAGS_2")
    assert flags2["progress"] == 0 and flags2["completed"] is False

    # 서울빵집 실버 정복 → 진행도 1
    await client.post(
        "/api/v1/flags",
        headers=h,
        json={"store_id": setup["서울"], "type": "SILVER"},
    )
    wk = (await client.get("/api/v1/missions/weekly", headers=h)).json()
    flags2 = next(m for m in wk["missions"] if m["code"] == "W_FLAGS_2")
    assert flags2["progress"] == 1

    # 미완료 상태에서 claim → 400
    early = await client.post("/api/v1/missions/W_FLAGS_2/claim", headers=h)
    assert early.status_code == 400

    # 부산빵집 실버 정복 → 깃발 2개 + 지역 2개 달성
    await client.post(
        "/api/v1/flags",
        headers=h,
        json={"store_id": setup["부산"], "type": "SILVER"},
    )
    wk = (await client.get("/api/v1/missions/weekly", headers=h)).json()
    m = {x["code"]: x for x in wk["missions"]}
    assert m["W_FLAGS_2"]["completed"] is True
    assert m["W_REGION_2"]["completed"] is True

    me_before = (await client.get("/api/v1/users/me", headers=h)).json()
    assert me_before["stat"]["exp"] == 100  # 실버 50 x 2

    claim = await client.post("/api/v1/missions/W_FLAGS_2/claim", headers=h)
    assert claim.status_code == 200, claim.text
    body = claim.json()
    assert body["reward_exp"] == 100
    assert body["exp"] == 200

    # 재수령 → 409
    dup = await client.post("/api/v1/missions/W_FLAGS_2/claim", headers=h)
    assert dup.status_code == 409

    wk = (await client.get("/api/v1/missions/weekly", headers=h)).json()
    assert next(x for x in wk["missions"] if x["code"] == "W_FLAGS_2")["claimed"] is True
    # 다른 미션은 아직 수령 가능
    r2 = await client.post("/api/v1/missions/W_REGION_2/claim", headers=h)
    assert r2.status_code == 200
    assert r2.json()["exp"] == 400  # 200 + 200

    me = (await client.get("/api/v1/users/me", headers=h)).json()
    assert me["stat"]["exp"] == 400


@pytest.mark.asyncio
async def test_unknown_mission_404(client, setup):
    h = await _auth(client, "누구", "who@test.dev")
    r = await client.post("/api/v1/missions/NOPE/claim", headers=h)
    assert r.status_code == 404
