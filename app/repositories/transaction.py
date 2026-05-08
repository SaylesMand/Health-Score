import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Репозиторий для учёта финансовых операций."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def add(
        self,
        user_id: int,
        amount: float,
        t_type: TransactionType,
        challenge_id: str | None = None,
    ) -> Transaction:
        """Добавляет запись о транзакции в текущую сессию."""
        db_transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=t_type,
            challenge_id=challenge_id,
        )
        self.session.add(db_transaction)
        logger.info(
            f"Транзакция подготовлена: user_id={user_id}, type={t_type.value}, amount={amount}"
        )
        return db_transaction
