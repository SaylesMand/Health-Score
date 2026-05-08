import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.repositories.transaction import TransactionRepository
from app.services.billing import BillingService


async def _make_user(session, balance: float = 0.0, loyalty_id: int = 1) -> User:
    """Создаёт пользователя в указанной сессии."""
    user = User(
        username=f"u_{int(balance)}",
        email=f"u_{int(balance)}@e.test",
        hashed_password=get_password_hash("p"),
        balance=balance,
        loyalty_level_id=loyalty_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_charge_for_prediction_deducts_base_price(db_session):
    """Списание Bronze-юзера снижает баланс ровно на 100."""
    user = await _make_user(db_session, balance=300, loyalty_id=1)
    service = BillingService(db_session)

    price = await service.charge_for_prediction(user.id)
    await db_session.commit()
    await db_session.refresh(user)

    assert price == 100.0
    assert user.balance == 200.0


async def test_charge_applies_silver_discount(db_session):
    """Silver-юзер получает скидку 5%."""
    user = await _make_user(db_session, balance=300, loyalty_id=2)
    price = await BillingService(db_session).charge_for_prediction(user.id)
    await db_session.commit()
    assert price == 95.0


async def test_charge_applies_gold_discount(db_session):
    """Gold-юзер получает скидку 10%."""
    user = await _make_user(db_session, balance=300, loyalty_id=3)
    price = await BillingService(db_session).charge_for_prediction(user.id)
    await db_session.commit()
    assert price == 90.0


async def test_charge_raises_402_on_insufficient_balance(db_session):
    """Недостаток средств приводит к HTTP 402."""
    user = await _make_user(db_session, balance=10)
    with pytest.raises(HTTPException) as exc:
        await BillingService(db_session).charge_for_prediction(user.id)
    assert exc.value.status_code == 402


async def test_charge_raises_404_on_unknown_user(db_session):
    """Неизвестный user_id приводит к HTTP 404."""
    with pytest.raises(HTTPException) as exc:
        await BillingService(db_session).charge_for_prediction(user_id=999_999)
    assert exc.value.status_code == 404


async def test_refund_reverts_balance(db_session):
    """Refund возвращает средства и пишет REFUND-транзакцию."""
    user = await _make_user(db_session, balance=50)
    await BillingService(db_session).refund(user.id, 30)
    await db_session.refresh(user)
    assert user.balance == 80.0

    txns = (
        (await db_session.execute(select(Transaction).where(Transaction.user_id == user.id)))
        .scalars()
        .all()
    )
    assert any(t.transaction_type == TransactionType.REFUND for t in txns)


async def test_refill_via_service(db_session):
    """Refill добавляет средства и возвращает новый баланс."""
    user = await _make_user(db_session, balance=0)
    new_balance = await BillingService(db_session).refill(user.id, 200)
    assert new_balance == 200.0


async def test_transaction_repository_add_does_not_commit(db_session):
    """Repository.add только готовит запись, без commit."""
    user = await _make_user(db_session, balance=0)
    repo = TransactionRepository(db_session)
    repo.add(user_id=user.id, amount=10, t_type=TransactionType.REFILL)
    assert "Transaction" in str(db_session.new)
