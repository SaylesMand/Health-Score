import asyncio
import secrets

from app.core.database import async_session_maker
from app.repositories.prediction import PredictionRepository
from app.tasks.config import celery_app


@celery_app.task(name="compute_health_prediction")
def compute_health_prediction(prediction_id: int, data: dict):
    """Фоновая задача для ML-предсказания."""
    return asyncio.run(_run_prediction_logic(prediction_id, data))


async def _run_prediction_logic(prediction_id: int, data: dict) -> None:
    await asyncio.sleep(2)
    probability = secrets.randbelow(100) / 100.0

    async with async_session_maker() as session:
        repo = PredictionRepository(session)
        await repo.update_result(
            prediction_id=prediction_id, probability=probability, price_charged=0.0
        )

    return probability
