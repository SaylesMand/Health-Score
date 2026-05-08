import logging
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.prediction import PredictionStatus
from app.models.user import User
from app.repositories.prediction import PredictionRepository
from app.schemas.health import HealthDataCreate, HealthPredictionRead
from app.services.billing import BillingService
from app.tasks.worker import compute_health_prediction

logger = logging.getLogger(__name__)

router = APIRouter()

_LEVEL_RANK = {"bronze": 1, "silver": 2, "gold": 3}


@router.get("/history", response_model=Sequence[HealthPredictionRead])
async def get_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """История предсказаний текущего пользователя."""
    predictions = await PredictionRepository(db).get_user_history(current_user.id)
    return [
        HealthPredictionRead(
            prediction_id=p.id,
            probability=p.result,
            status=p.status,
        )
        for p in predictions
    ]


@router.post("/predict", response_model=HealthPredictionRead)
async def predict(
    data: HealthDataCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Списывает кредиты и ставит предсказание в очередь."""
    user_with_level = await db.execute(
        select(User).where(User.id == current_user.id).options(selectinload(User.loyalty_level))
    )
    user = user_with_level.scalar_one()
    user_level = user.loyalty_level.name.lower() if user.loyalty_level else "bronze"
    req_level = data.model_type.value

    if _LEVEL_RANK.get(req_level, 1) > _LEVEL_RANK.get(user_level, 1):
        logger.warning(
            f"Отказ в доступе: user={user.id}, требует={req_level}, уровень={user_level}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Модель {req_level.title()} недоступна. Ваш уровень: {user_level.title()}",
        )

    billing = BillingService(db)
    predictions = PredictionRepository(db)

    price_charged = await billing.charge_for_prediction(user.id)
    input_dict = data.model_dump()
    new_prediction = await predictions.add(user_id=user.id, input_data=input_dict)
    await db.commit()

    try:
        compute_health_prediction.delay(
            prediction_id=new_prediction.id,
            data=input_dict,
            price=price_charged,
            loyalty_level=req_level,
        )
    except Exception:
        logger.exception(
            f"Не удалось поставить задачу в Celery: prediction_id={new_prediction.id}. "
            "Выполняю refund."
        )
        await predictions.update_status(new_prediction.id, PredictionStatus.FAILED)
        await billing.refund(user.id, price_charged)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис очередей недоступен. Средства возвращены.",
        ) from None

    logger.info(
        f"Задача предсказания поставлена в очередь: user_id={user.id}, "
        f"prediction_id={new_prediction.id}"
    )
    return HealthPredictionRead(
        prediction_id=new_prediction.id,
        probability=None,
        status=PredictionStatus.PENDING,
    )
