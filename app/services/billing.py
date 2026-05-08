import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.transaction import TransactionRepository

logger = logging.getLogger(__name__)


class BillingService:
    """Сервис финансовых операций (биллинг)."""

    BASE_PREDICTION_PRICE = 100.0

    def __init__(self, session: AsyncSession):
        self.session = session
        self.transactions = TransactionRepository(session)

    @staticmethod
    def _final_price(discount_rate: float) -> float:
        return round(BillingService.BASE_PREDICTION_PRICE * (1 - discount_rate), 2)

    async def charge_for_prediction(self, user_id: int) -> float:
        """Списывает кредиты за предсказание в текущей транзакции."""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.loyalty_level))
            .with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден."
            )

        discount = user.loyalty_level.discount_rate if user.loyalty_level else 0.0
        price = self._final_price(discount)

        if user.balance < price:
            logger.warning(
                f"Недостаточно средств: user={user_id}, требуется={price}, баланс={user.balance}"
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Недостаточно кредитов. Требуется: {price}, на балансе: {user.balance}",
            )

        user.balance -= price
        self.transactions.add(user_id=user.id, amount=price, t_type=TransactionType.PAYMENT)
        logger.info(f"Подготовлено списание: user={user_id}, сумма={price}")
        return price

    async def refund(self, user_id: int, amount: float) -> None:
        """Компенсирующий возврат средств. Выполняется отдельной транзакцией."""
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            logger.error(f"Refund невозможен: пользователь {user_id} не найден")
            return
        user.balance += amount
        self.transactions.add(user_id=user_id, amount=amount, t_type=TransactionType.REFUND)
        await self.session.commit()
        logger.info(f"Refund выполнен: user={user_id}, сумма={amount}")

    async def refill(self, user_id: int, amount: float) -> float:
        """Пополнение баланса. Коммитит в рамках своего вызова."""
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден."
            )
        user.balance += amount
        self.transactions.add(user_id=user_id, amount=amount, t_type=TransactionType.REFILL)
        await self.session.commit()
        logger.info(f"Пополнение: user={user_id}, сумма={amount}, новый баланс={user.balance}")
        return user.balance
