"""매장/게시판 검색·필터 (F-SEARCH)."""

from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.enums import EvidenceType, FlagType, StoreCreatedSource, StoreStatus
from app.models.flag import Flag
from app.models.review import Review
from app.models.store import Store, StoreStat
from app.models.user import User, UserStat


def _store(name, sido, category, lat, *, verified=False) -> Store:
    s = Store(
        name=name,
        address=f"{sido} 어딘가",
        region_sido=sido,
        lat=Decimal(str(lat)),
        lng=Decimal("127.0"),
        category=category,
        created_source=StoreCreatedSource.AUTO_COLLECTED,
        status=StoreStatus.ACTIVE,
        is_verified_owner=verified,
    )
    s.stat = StoreStat()
    return s


@pytest_asyncio.fixture
async def data(db_session):
    users = [User(nickname=f"x{i}", email=f"x{i}@t.dev", password_hash="p") for i in range(4)]
    for u in users:
        u.stat = UserStat()
    seongsu = _store("성수 크루아상", "서울", "베이커리", 37.10, verified=True)
    jongno = _store("종로 소금빵", "서울", "베이커리", 37.20)
    busan = _store("부산 밤식빵", "부산", "디저트", 35.10)
    closed = _store("폐점 빵집", "서울", "베이커리", 37.30)
    closed.status = StoreStatus.CLOSED
    db_session.add_all([*users, seongsu, jongno, busan, closed])
    await db_session.flush()

    # 정복자: 성수 3명, 종로 1명
    def flag(uid, sid):
        return Flag(
            user_id=uid, store_id=sid, type=FlagType.SILVER,
            evidence_type=EvidenceType.NONE, exp_granted=50,
        )

    db_session.add_all(
        [flag(users[0].id, seongsu.id), flag(users[1].id, seongsu.id),
         flag(users[2].id, seongsu.id), flag(users[0].id, jongno.id)]
    )
    seongsu.stat.conqueror_count = 3
    jongno.stat.conqueror_count = 1
    # 평점: 종로 5.0, 성수 3.0
    db_session.add_all(
        [Review(user_id=users[0].id, store_id=jongno.id, rating=Decimal("5.0")),
         Review(user_id=users[0].id, store_id=seongsu.id, rating=Decimal("3.0"))]
    )
    seongsu.stat.average_rating = Decimal("3.0")
    jongno.stat.average_rating = Decimal("5.0")
    await db_session.commit()
    return {"seongsu": seongsu.id, "jongno": jongno.id, "busan": busan.id}


@pytest.mark.asyncio
async def test_store_search_filters_and_sort(client, data):
    async def search(**qs):
        query = "&".join(f"{k}={v}" for k, v in qs.items())
        return (await client.get(f"/api/v1/stores/search?{query}")).json()

    # 키워드 (이름)
    r = await search(q="소금빵")
    assert r["total"] == 1 and r["items"][0]["id"] == data["jongno"]

    # 지역
    assert (await search(region_sido="부산"))["total"] == 1

    # 카테고리 (CLOSED 는 제외)
    assert (await search(category="베이커리"))["total"] == 2

    # 인증 매장만
    ver = await search(verified_only="true")
    assert ver["total"] == 1 and ver["items"][0]["id"] == data["seongsu"]

    # 정렬: popular → 성수 먼저
    pop = await search(sort="popular")
    assert [i["id"] for i in pop["items"][:2]] == [data["seongsu"], data["jongno"]]

    # 정렬: rating → 종로 먼저
    rat = await search(sort="rating")
    assert [i["id"] for i in rat["items"][:2]] == [data["jongno"], data["seongsu"]]

    # 페이지네이션: total 은 전체, items 는 제한
    page = await search(limit=1, offset=0)
    assert page["total"] == 3 and len(page["items"]) == 1


@pytest.mark.asyncio
async def test_store_filters_endpoint(client, data):
    f = (await client.get("/api/v1/stores/filters")).json()
    assert f["regions"] == ["부산", "서울"]
    assert f["categories"] == ["디저트", "베이커리"]


@pytest.mark.asyncio
async def test_search_route_does_not_shadow_detail(client, data):
    # /stores/search 가 /stores/{id} 를 가리지 않아야 한다
    detail = await client.get(f"/api/v1/stores/{data['seongsu']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "성수 크루아상"


@pytest.mark.asyncio
async def test_post_search_and_sort(client, data):
    await client.post(
        "/api/v1/auth/register",
        json={"nickname": "writer", "email": "w@t.dev", "password": "password123"},
    )
    h = {
        "Authorization": "Bearer "
        + (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "w@t.dev", "password": "password123"},
            )
        ).json()["access_token"]
    }
    p1 = (
        await client.post(
            "/api/v1/posts",
            headers=h,
            json={
                "title": "크루아상 맛집 추천",
                "content": "성수동",
                "store_id": data["seongsu"],
            },
        )
    ).json()["id"]
    await client.post(
        "/api/v1/posts",
        headers=h,
        json={"title": "소금빵 투어", "content": "종로"},
    )

    await client.post(f"/api/v1/posts/{p1}/like", headers=h)

    kw = (await client.get("/api/v1/posts?q=크루아상")).json()
    assert len(kw) == 1 and kw[0]["id"] == p1

    by_store = (await client.get(f"/api/v1/posts?store_id={data['seongsu']}")).json()
    assert [p["id"] for p in by_store] == [p1]

    pop = (await client.get("/api/v1/posts?sort=popular")).json()
    assert pop[0]["id"] == p1  # 좋아요 1개로 최상단
