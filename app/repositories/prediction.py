from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction, PredictionStatus


class PredictionRepository:
    """Репозиторий для работы с предсказаниями в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, input_data: dict[str, Any]) -> Prediction:
        """Создает новое предсказание в статусе pending."""
        db_prediction = Prediction(
            user_id=user_id, input_data=input_data, status=PredictionStatus.PENDING
        )
        self.session.add(db_prediction)
        await self.session.commit()

        await self.session.refresh(db_prediction)

        return db_prediction

    async def get_by_id(self, prediction_id: int) -> Prediction | None:
        """Получает детали предсказания по ID."""
        query = select(Prediction).where(Prediction.id == prediction_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_result(
        self, prediction_id: int, result: float, price_charged: float
    ) -> Prediction | None:
        """Обновляет результат предсказания."""
        db_prediction = await self.get_by_id(prediction_id)
        if not db_prediction:
            return

        db_prediction.result = result
        db_prediction.price_charged = price_charged
        db_prediction.status = PredictionStatus.COMPLETED

        await self.session.commit()
        await self.session.refresh(db_prediction)

        return db_prediction

    async def get_user_history(self, user_id: int) -> Sequence[Prediction]:
        """Получает историю предсказаний пользователя."""
        query = (
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .order_by(Prediction.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
