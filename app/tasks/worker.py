import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import async_session_maker
from app.ml.model import ml_model
from app.models.loyalty_level import LoyaltyLevel
from app.models.prediction import Prediction, PredictionStatus
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.repositories.prediction import PredictionRepository
from app.tasks.config import celery_app

logger = logging.getLogger(__name__)


class PredictionTask(celery_app.Task):
    """Базовый класс таски: после исчерпания retry возвращает кредиты."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Возвращает кредиты, если задача окончательно упала."""
        prediction_id = kwargs.get("prediction_id") if kwargs else None
        price = kwargs.get("price") if kwargs else None
        if prediction_id is None and args:
            prediction_id = args[0]
        if price is None and args and len(args) > 2:
            price = args[2]
        if prediction_id is None or price is None:
            logger.error(f"on_failure: нет prediction_id/price в task={task_id}")
            return
        try:
            asyncio.run(_finalize_failed_prediction(int(prediction_id), float(price)))
        except Exception:
            logger.exception(f"on_failure refund провален: prediction_id={prediction_id}")


@celery_app.task(name="compute_health_prediction", base=PredictionTask, bind=True, max_retries=3)
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


async def _finalize_failed_prediction(prediction_id: int, price: float) -> None:
    """Idempotent: в одной транзакции помечает FAILED и возвращает price."""
    async with async_session_maker() as session:
        prediction = await session.get(Prediction, prediction_id, with_for_update=True)
        if prediction is None:
            logger.error(f"finalize_failed: prediction id={prediction_id} не найден")
            return
        if prediction.refunded:
            logger.info(f"finalize_failed: prediction id={prediction_id} уже refunded")
            return

        user = await session.get(User, prediction.user_id, with_for_update=True)
        if user is None:
            logger.error(f"finalize_failed: user id={prediction.user_id} не найден")
            return
        user.balance += price
        session.add(
            Transaction(user_id=user.id, amount=price, transaction_type=TransactionType.REFUND)
        )
        prediction.status = PredictionStatus.FAILED
        prediction.refunded = True
        await session.commit()
        logger.info(f"finalize_failed: prediction id={prediction_id}, возвращено {price}")


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
            prediction_id=prediction_id, result=probability
        )
    return probability


@celery_app.task(name="cleanup_stale_predictions")
def cleanup_stale_predictions():
    """Watchdog: pending старше PREDICTION_STALE_AFTER_MINUTES → FAILED + refund."""
    logger.info("Старт watchdog по pending-предсказаниям")
    asyncio.run(_run_cleanup_stale_predictions())


async def _run_cleanup_stale_predictions() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.PREDICTION_STALE_AFTER_MINUTES)
    async with async_session_maker() as session:
        stale = await session.execute(
            select(Prediction.id, Prediction.price_charged).where(
                Prediction.status == PredictionStatus.PENDING,
                Prediction.refunded.is_(False),
                Prediction.created_at < cutoff,
            )
        )
        rows = stale.all()

    for prediction_id, price_charged in rows:
        if not price_charged:
            continue
        logger.warning(f"Watchdog: prediction id={prediction_id} завис, refund {price_charged}")
        await _finalize_failed_prediction(prediction_id, float(price_charged))


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
