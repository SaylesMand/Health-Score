import os

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("SECRET_KEY", "test_secret_key_at_least_16_chars")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

import asyncio
from concurrent.futures import ThreadPoolExecutor

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

import app.api.endpoints.gamification as gamification_module
import app.api.endpoints.predict as predict_module
import app.core.database as db_module
import app.tasks.worker as worker_module
from app.core.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.loyalty_level import LoyaltyLevel
from app.models.user import User


@pytest.fixture(scope="session")
def _ml_executor():
    """Однопоточный executor, в котором синхронно выполняется ML-логика тестов."""
    pool = ThreadPoolExecutor(max_workers=1)
    yield pool
    pool.shutdown(wait=True)


@pytest.fixture(autouse=True)
def _patch_predict_task(monkeypatch, _ml_executor):
    """Заменяет compute_health_prediction.delay на синхронный запуск в отдельном loop."""

    def fake_delay(prediction_id, data, price, loyalty_level):
        future = _ml_executor.submit(
            asyncio.run,
            worker_module._run_prediction_logic(prediction_id, data, price, loyalty_level),
        )
        future.result()

    class _FakeTask:
        delay = staticmethod(fake_delay)

    monkeypatch.setattr(predict_module, "compute_health_prediction", _FakeTask)


@pytest.fixture(scope="session")
def pg_container():
    """Поднимает Postgres-контейнер на всю сессию тестов."""
    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(pg_container) -> str:
    """URL тестовой БД для asyncpg."""
    return pg_container.get_connection_url().replace("psycopg2", "asyncpg")


@pytest_asyncio.fixture(scope="session")
async def engine(database_url):
    """Session-scoped async-engine с NullPool: один pool на всю сессию тестов."""
    eng = create_async_engine(database_url, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session_maker = async_sessionmaker(eng, expire_on_commit=False)
    db_module.engine = eng
    db_module.async_session_maker = test_session_maker
    worker_module.async_session_maker = test_session_maker
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Чистая сессия для прямой работы с БД."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _clean_db(engine):
    """Очищает таблицы и пересидит уровни лояльности перед каждым тестом."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE transactions, predictions, users, "
                "loyalty_levels RESTART IDENTITY CASCADE"
            )
        )
        session.add_all(
            [
                LoyaltyLevel(name="Bronze", discount_rate=0.0, min_spend=0.0),
                LoyaltyLevel(name="Silver", discount_rate=0.05, min_spend=500.0),
                LoyaltyLevel(name="Gold", discount_rate=0.1, min_spend=1000.0),
            ]
        )
        await session.commit()
    yield


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch):
    """Подменяет Redis-клиент геймификации на in-memory fake."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(gamification_module, "redis_client", fake)
    yield fake


@pytest_asyncio.fixture
async def client(engine):
    """HTTP-клиент с переопределённой DB-сессией FastAPI."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client) -> dict:
    """Регистрирует тестового пользователя и возвращает его данные с токеном."""
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "secret123",
    }
    res = await client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    user = res.json()

    res = await client.post(
        "/api/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"user": user, "token": token, "auth": {"Authorization": f"Bearer {token}"}}


@pytest_asyncio.fixture
async def admin_user(client, engine) -> dict:
    """Создаёт пользователя с ролью admin и возвращает его токен."""
    from app.core.security import get_password_hash
    from app.models.user import UserRole

    payload = {"username": "root", "email": "root@example.com", "password": "rootpass1"}
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        user = User(
            username=payload["username"],
            email=payload["email"],
            hashed_password=get_password_hash(payload["password"]),
            role=UserRole.ADMIN,
            loyalty_level_id=1,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        admin_id = user.id

    res = await client.post(
        "/api/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {
        "id": admin_id,
        "token": token,
        "auth": {"Authorization": f"Bearer {token}"},
    }
