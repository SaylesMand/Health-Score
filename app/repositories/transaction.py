from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType
from app.models.user import User


class TransactionRepository:
    """Репозиторий для учета всех финансовых операций (биллинг)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, amount: float, t_type: TransactionType) -> Transaction:
        """Создает запись о транзакции пользователя."""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return

        db_transaction = Transaction(user_id=user_id, amount=amount, transaction_type=t_type)
        self.session.add(db_transaction)

        if t_type == TransactionType.REFILL:
            user.balance += amount
        elif t_type == TransactionType.PAYMENT:
            user.balance -= amount

        await self.session.commit()
        await self.session.refresh(db_transaction)

        return db_transaction
