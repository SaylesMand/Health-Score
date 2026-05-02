from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loyalty_level import LoyaltyLevel
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.transaction import TransactionRepository


class BillingService:
    """Сервис дял обработки финансовых операций (биллинг)."""

    BASE_PREDICTION_PRICE = 100.0

    def __init__(self, session: AsyncSession):
        self.session = session
        self.transaction_repo = TransactionRepository(session)

    async def calculate_prediction_price(self, user: User) -> float:
        """Расчитывает стоимость предсказания с учетом скидки для пользователя."""
        query = select(LoyaltyLevel).where(LoyaltyLevel.id == user.loyalty_level_id)
        result = await self.session.execute(query)
        loyalty = result.scalar_one_or_none()

        if not loyalty:
            return self.BASE_PREDICTION_PRICE

        discount = loyalty.discount_rate
        final_price = self.BASE_PREDICTION_PRICE * (1 - discount)
        return round(final_price, 2)

    async def charge_for_prediction(self, user_id: int) -> float:
        """Атомарно списывает средства за предсказание."""
        query = select(User).where(User.id == user_id).with_for_update()
        result = await self.session.execute(query)
        current_user = result.scalar_one_or_none()

        price = await self.calculate_prediction_price(current_user)

        if current_user.balance < price:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Недостаточно кредитов. Требуется: {price}, "
                f"на балансе: {current_user.balance}",
            )

        await self.transaction_repo.create(
            user_id=current_user.id, amount=price, t_type=TransactionType.PAYMENT
        )

        return price
