import logging
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction, PredictionStatus

logger = logging.getLogger(__name__)


class PredictionRepository:
    """Репозиторий предсказаний."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, input_data: dict[str, Any]) -> Prediction:
        """Добавляет запись со статусом pending и делает flush, чтобы получить id."""
        prediction = Prediction(
            user_id=user_id,
            input_data=input_data,
            status=PredictionStatus.PENDING,
        )
        self.session.add(prediction)
        await self.session.flush()
        logger.info(f"Prediction подготовлено: id={prediction.id}, user={user_id}")
        return prediction

    async def get_by_id(self, prediction_id: int) -> Prediction | None:
        """Получает предсказание по ID."""
        result = await self.session.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        return result.scalar_one_or_none()

    async def update_result(
        self, prediction_id: int, result: float, price_charged: float
    ) -> Prediction | None:
        """Идемпотентно сохраняет результат: повторный вызов на COMPLETED - no-op."""
        prediction = await self.get_by_id(prediction_id)
        if prediction is None:
            logger.error(f"Prediction id={prediction_id} не найден при update_result")
            return None
        if prediction.status == PredictionStatus.COMPLETED:
            logger.info(f"Prediction id={prediction_id} уже COMPLETED - пропуск")
            return prediction
        prediction.result = result
        prediction.price_charged = price_charged
        prediction.status = PredictionStatus.COMPLETED
        await self.session.commit()
        return prediction

    async def get_user_history(self, user_id: int) -> Sequence[Prediction]:
        """Получает историю предсказаний пользователя."""
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .order_by(Prediction.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(
        self, prediction_id: int, status: PredictionStatus
    ) -> Prediction | None:
        """Идемпотентно сохраняет статус."""
        prediction = await self.get_by_id(prediction_id)
        if prediction is None:
            logger.error(f"Prediction id={prediction_id} не найден при update_status")
            return None
        prediction.status = status
        await self.session.commit()
        return prediction
