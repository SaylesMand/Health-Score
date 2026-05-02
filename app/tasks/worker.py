import asyncio
import secrets

from sqlalchemy import func, select

from app.core.database import async_session_maker
from app.models.loyalty_level import LoyaltyLevel
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.repositories.prediction import PredictionRepository
from app.tasks.config import celery_app


@celery_app.task(name="compute_health_prediction")
def compute_health_prediction(prediction_id: int, data: dict, price: float):
    """Фоновая задача для ML-предсказания."""
    return asyncio.run(_run_prediction_logic(prediction_id, data, price))


async def _run_prediction_logic(prediction_id: int, data: dict, price: float) -> None:
    await asyncio.sleep(2)
    probability = secrets.randbelow(100) / 100.0

    async with async_session_maker() as session:
        repo = PredictionRepository(session)
        await repo.update_result(
            prediction_id=prediction_id, probability=probability, price_charged=price
        )

    return probability


@celery_app.task(name="update_loyalty_levels")
def update_loyalty_levels():
    """Перерасчет уровней лояльности."""
    return asyncio.run(_run_loyalty_update())


async def _run_loyalty_update():
    async with async_session_maker() as session:
        levels_res = await session.execute(
            select(LoyaltyLevel).order_by(LoyaltyLevel.min_spend.desc())
        )
        levels = levels_res.scalars().all()

        users_res = await session.execute(select(User))
        users = users_res.scalars().all()

        for user in users:
            spend_res = await session.execute(
                select(func.sum(Transaction.amount)).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == TransactionType.PAYMENT,
                )
            )
            total_spent = spend_res.scalar() or 0.0

            new_level_id = user.loyalty_level_id
            for level in levels:
                if total_spent >= level.min_spend:
                    new_level_id = level.id
                    break

            if new_level_id != user.loyalty_level_id:
                user.loyalty_level_id = new_level_id

        await session.commit()
