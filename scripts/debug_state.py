import asyncio

from sqlalchemy import func, select

from app.core.database import async_session_maker
from app.models.loyalty_level import LoyaltyLevel
from app.models.transaction import Transaction, TransactionType
from app.models.user import User


async def check_state():
    """Проверка состояния базы данных."""
    async with async_session_maker() as session:
        # Check users
        print("--- Users ---")
        users_res = await session.execute(
            select(User.id, User.username, User.loyalty_level_id, User.balance)
        )
        for row in users_res.all():
            # Calculate total spent for this user
            spend_res = await session.execute(
                select(func.sum(Transaction.amount)).where(
                    Transaction.user_id == row.id,
                    Transaction.transaction_type == TransactionType.PAYMENT,
                )
            )
            total_spent = spend_res.scalar() or 0.0
            print(
                f"ID: {row.id}, User: {row.username}, Level: {row.loyalty_level_id}, "
                f"Balance: {row.balance}, Total Spent: {total_spent}"
            )

        # Check loyalty levels thresholds
        print("\n--- Loyalty Levels ---")
        levels_res = await session.execute(
            select(LoyaltyLevel).order_by(LoyaltyLevel.min_spend.asc())
        )
        for level in levels_res.scalars().all():
            print(
                f"ID: {level.id}, Name: {level.name}, Min Spend: {level.min_spend}, "
                f"Discount: {level.discount_rate}"
            )


if __name__ == "__main__":
    asyncio.run(check_state())
