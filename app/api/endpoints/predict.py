from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.prediction import PredictionStatus
from app.models.user import User
from app.repositories.prediction import PredictionRepository
from app.schemas.health import HealthDataCreate, HealthPredictionRead
from app.tasks.worker import compute_health_prediction

router = APIRouter()


@router.post("/predict", response_model=HealthPredictionRead)
async def predict(
    data: HealthDataCreate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Предсказание вероятности наличия сердечно-сосудистых заболеваний."""
    prediction_repo = PredictionRepository(db)
    input_dict = data.model_dump()

    new_prediction = await prediction_repo.create(user_id=current_user.id, input_data=input_dict)

    compute_health_prediction.delay(prediction_id=new_prediction.id, data=input_dict)

    return HealthPredictionRead(
        prediction_id=new_prediction.id,
        probability=None,
        status=PredictionStatus.PENDING,
    )
