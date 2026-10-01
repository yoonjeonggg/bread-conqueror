import contextlib
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_db
from app.db.base_class import Base
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def _engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(_engine, db_session) -> AsyncGenerator[AsyncClient, None]:
    maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def _reset_redis_pool():
    """각 테스트는 자체 이벤트 루프를 쓴다. 모듈 전역 redis 클라이언트의
    커넥션 풀이 이전 루프에 묶여 있으면 다음 테스트에서 'Event loop is closed'
    가 나므로, 테스트마다 풀을 닫아 재연결을 유도한다."""
    yield
    from app.core.redis import redis_client

    with contextlib.suppress(Exception):
        await redis_client.aclose()


class FakeThrottleRedis:
    """Just enough of redis.asyncio for services/login_throttle — TTLs are
    tracked but never elapse, which is what the lockout tests want."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        value = self.values.get(key)
        return None if value is None else str(value)

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -2)

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.ttls.pop(key, None)

    def pipeline(self) -> "FakeThrottleRedis._Pipeline":
        return self._Pipeline(self)

    class _Pipeline:
        def __init__(self, redis: "FakeThrottleRedis") -> None:
            self.redis = redis
            self.ops: list[tuple[str, str, int]] = []

        def incr(self, key: str) -> None:
            self.ops.append(("incr", key, 0))

        def expire(self, key: str, seconds: int) -> None:
            self.ops.append(("expire", key, seconds))

        async def execute(self) -> None:
            for op, key, arg in self.ops:
                if op == "incr":
                    self.redis.values[key] = self.redis.values.get(key, 0) + 1
                else:
                    self.redis.ttls[key] = arg


@pytest.fixture(autouse=True)
def throttle_redis(monkeypatch) -> FakeThrottleRedis:
    """Login throttling talks to Redis; give each test its own in-memory one so
    attempts never leak between tests (or depend on a running Redis)."""
    from app.api.v1.routers import auth

    fake = FakeThrottleRedis()
    monkeypatch.setattr(auth, "redis_client", fake)
    return fake
