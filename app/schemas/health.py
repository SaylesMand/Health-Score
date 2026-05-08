import enum

from pydantic import BaseModel, Field


class ModelTier(str, enum.Enum):
    """Уровень доступной ML-модели (привязан к loyalty-уровню)."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class HealthDataCreate(BaseModel):
    # https://www.kaggle.com/datasets/sulianova/cardiovascular-disease-dataset
    """Входные биометрические данные для предсказания."""

    age: int = Field(..., ge=0, le=120, description="Возраст в годах")
    gender: int = Field(..., ge=1, le=2, description="Пол (1 - женский, 2 - мужской)")
    height: int = Field(..., ge=50, le=250, description="Рост в см")
    weight: float = Field(..., ge=30, le=300, description="Вес в кг")
    ap_hi: int = Field(..., ge=40, le=250, description="Систолическое давление")
    ap_lo: int = Field(..., ge=30, le=180, description="Диастолическое давление")
    cholesterol: int = Field(..., ge=1, le=3, description="Уровень холестерина (1-3)")
    gluc: int = Field(..., ge=1, le=3, description="Уровень глюкозы (1-3)")
    smoke: int = Field(..., ge=0, le=1, description="Курение (0/1)")
    alco: int = Field(..., ge=0, le=1, description="Употребление алкоголя (0/1)")
    active: int = Field(..., ge=0, le=1, description="Физическая активность (0/1)")
    model_type: ModelTier = Field(
        ModelTier.BRONZE, description="Желаемая модель: bronze, silver или gold"
    )


class HealthPredictionRead(BaseModel):
    """Результат предсказания."""

    prediction_id: int = Field(..., description="ID записи предсказания")
    probability: float | None = Field(
        ..., description="Вероятность наличия сердечно-сосудистых заболеваний"
    )
    status: str = Field(..., description="Статус обработки")
