from pydantic import BaseModel, Field


class HealthDataCreate(BaseModel):
    # https://www.kaggle.com/datasets/sulianova/cardiovascular-disease-dataset
    """Модель для входных данных анализа здоровья."""

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

    def to_model_input(self):
        """Метод для преобразования данных в формат модели."""
        return {
            "age": int(self.age * 365.25),
            "gender": self.gender,
            "height": self.height,
            "weight": self.weight,
            "ap_hi": self.ap_hi,
            "ap_lo": self.ap_lo,
            "cholesterol": self.cholesterol,
            "gluc": self.gluc,
            "smoke": self.smoke,
            "alco": self.alco,
            "active": self.active,
        }


class HealthPredictionRead(BaseModel):
    """Модель для возврата результата предсказания."""

    prediction_id: int = Field(..., description="ID записи предсказания")
    probability: float = Field(
        ..., description="Вероятность наличия сердечно-сосудистых заболеваний"
    )
    status: str = Field(..., description="Статус обработки")
