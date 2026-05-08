from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.tasks.worker as worker_module
from app.core.security import get_password_hash
from app.models.transaction import Transaction, TransactionType
from app.models.user import User


@pytest_asyncio.fixture
async def make_user(engine):
    """Фабрика пользователей в тестовой БД."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    created: list[int] = []

    async def _make(loyalty_id: int = 1) -> int:
        async with sessionmaker() as session:
            user = User(
                username=f"loy_{len(created)}",
                email=f"loy_{len(created)}@e.test",
                hashed_password=get_password_hash("p"),
                balance=10_000,
                loyalty_level_id=loyalty_id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            created.append(user.id)
            return user.id

    yield _make


@pytest_asyncio.fixture
async def add_payment(engine):
    """Записывает PAYMENT-транзакцию указанному юзеру."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _add(user_id: int, amount: float, days_ago: int = 1) -> None:
        async with sessionmaker() as session:
            txn = Transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.PAYMENT,
            )
            session.add(txn)
            await session.flush()
            txn.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
            await session.commit()

    yield _add


async def test_loyalty_recalc_promotes_to_silver(engine, monkeypatch, make_user, add_payment):
    """Пользователь с тратами >=100 за 30 дней становится Silver."""
    monkeypatch.setattr(
        worker_module, "async_session_maker", async_sessionmaker(engine, expire_on_commit=False)
    )
    user_id = await make_user(loyalty_id=1)
    await add_payment(user_id, 150, days_ago=5)

    await worker_module._run_loyalty_update()

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        assert user.loyalty_level_id == 2


async def test_loyalty_recalc_promotes_to_gold(engine, monkeypatch, make_user, add_payment):
    """Пользователь с тратами >=500 за 30 дней становится Gold."""
    monkeypatch.setattr(
        worker_module, "async_session_maker", async_sessionmaker(engine, expire_on_commit=False)
    )
    user_id = await make_user(loyalty_id=1)
    await add_payment(user_id, 600, days_ago=5)

    await worker_module._run_loyalty_update()

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        assert user.loyalty_level_id == 3


async def test_loyalty_recalc_demotes_inactive_user(engine, monkeypatch, make_user, add_payment):
    """Пользователь без трат за 30 дней откатывается в Bronze."""
    monkeypatch.setattr(
        worker_module, "async_session_maker", async_sessionmaker(engine, expire_on_commit=False)
    )
    user_id = await make_user(loyalty_id=3)
    await add_payment(user_id, 1000, days_ago=60)

    await worker_module._run_loyalty_update()

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        assert user.loyalty_level_id == 1
