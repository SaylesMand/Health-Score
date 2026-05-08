import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.database import async_session_maker
from app.ml.model import ml_model
from app.models.loyalty_level import LoyaltyLevel
from app.models.prediction import PredictionStatus
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.repositories.prediction import PredictionRepository
from app.tasks.config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="compute_health_prediction", bind=True, max_retries=3)
def compute_health_prediction(
    self, prediction_id: int, data: dict, price: float, loyalty_level: str = "Bronze"
):
    """Фоновая задача ML-предсказания."""
    logger.info(f"Старт ML-предсказания: prediction_id={prediction_id}, level={loyalty_level}")
    try:
        return asyncio.run(_run_prediction_logic(prediction_id, data, price, loyalty_level))
    except Exception as exc:
        logger.exception(f"Сбой задачи prediction_id={prediction_id}: {exc}")
        raise self.retry(exc=exc, countdown=10) from exc


async def _run_prediction_logic(
    prediction_id: int, data: dict, price: float, loyalty_level: str
) -> float | None:
    try:
        probability = ml_model.predict_probability(data, loyalty_level)
    except Exception:
        async with async_session_maker() as session:
            await PredictionRepository(session).update_status(
                prediction_id, PredictionStatus.FAILED
            )
        raise

    async with async_session_maker() as session:
        await PredictionRepository(session).update_result(
            prediction_id=prediction_id, result=probability, price_charged=price
        )
    return probability


@celery_app.task(name="update_loyalty_levels")
def update_loyalty_levels():
    """Ежемесячный пересчёт уровней лояльности."""
    logger.info("Старт пересчёта уровней лояльности")
    asyncio.run(_run_loyalty_update())
    logger.info("Пересчёт уровней завершён")


async def _run_loyalty_update():
    async with async_session_maker() as session:
        levels_res = await session.execute(
            select(LoyaltyLevel).order_by(LoyaltyLevel.min_spend.desc())
        )
        levels = levels_res.scalars().all()
        if not levels:
            logger.warning("Уровни лояльности не сидированы - задача пропущена")
            return

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        users_res = await session.execute(select(User).with_for_update())
        for user in users_res.scalars():
            spend_res = await session.execute(
                select(func.sum(Transaction.amount)).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == TransactionType.PAYMENT,
                    Transaction.created_at >= thirty_days_ago,
                )
            )
            total_spent = spend_res.scalar() or 0.0

            new_level_id = user.loyalty_level_id
            for level in levels:
                if total_spent >= level.min_spend:
                    new_level_id = level.id
                    break

            if new_level_id != user.loyalty_level_id:
                logger.info(
                    f"User {user.id}: уровень {user.loyalty_level_id} -> {new_level_id} "
                    f"(потрачено за 30д: {total_spent})"
                )
                user.loyalty_level_id = new_level_id

        await session.commit()
