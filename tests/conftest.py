import os

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("SECRET_KEY", "test_secret_key_at_least_16_chars")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import app.api.endpoints.gamification as gamification_module
from app.core.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.loyalty_level import LoyaltyLevel
from app.tasks.config import celery_app


@pytest.fixture(scope="session", autouse=True)
def _celery_eager():
    """Запускает Celery-задачи синхронно в тестах."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture(scope="session")
def pg_container():
    """Поднимает Postgres-контейнер на всю сессию тестов."""
    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session")
async def engine(pg_container):
    """Async-engine на тестовой БД с накатанными моделями."""
    url = pg_container.get_connection_url().replace("psycopg2", "asyncpg")
    eng = create_async_engine(url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Чистая сессия с автооткатом всех изменений после теста."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _clean_db(engine):
    """Чистит таблицы между тестами и пересидит уровни лояльности."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        await session.execute(LoyaltyLevel.__table__.delete())
        from app.models.prediction import Prediction
        from app.models.transaction import Transaction
        from app.models.user import User

        await session.execute(Transaction.__table__.delete())
        await session.execute(Prediction.__table__.delete())
        await session.execute(User.__table__.delete())
        await session.commit()
        session.add_all(
            [
                LoyaltyLevel(name="Bronze", discount_rate=0.0, min_spend=0.0),
                LoyaltyLevel(name="Silver", discount_rate=0.05, min_spend=100.0),
                LoyaltyLevel(name="Gold", discount_rate=0.1, min_spend=500.0),
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
    payload = {"username": "alice", "email": "alice@example.com", "password": "secret123"}
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
    from app.models.user import User, UserRole

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
    return {"id": admin_id, "token": token, "auth": {"Authorization": f"Bearer {token}"}}
