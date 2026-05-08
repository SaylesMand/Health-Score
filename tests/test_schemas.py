import pytest
from pydantic import ValidationError

from app.schemas.health import HealthDataCreate, ModelTier


def _valid_payload(**overrides) -> dict:
    """Возвращает валидный payload для HealthDataCreate с возможностью переопределения."""
    base = {
        "age": 30,
        "gender": 1,
        "height": 170,
        "weight": 70.0,
        "ap_hi": 120,
        "ap_lo": 80,
        "cholesterol": 1,
        "gluc": 1,
        "smoke": 0,
        "alco": 0,
        "active": 1,
    }
    base.update(overrides)
    return base


def test_health_data_create_defaults_to_bronze():
    """По умолчанию выбирается модель Bronze."""
    obj = HealthDataCreate(**_valid_payload())
    assert obj.model_type is ModelTier.BRONZE


def test_health_data_create_accepts_silver_string():
    """Строковое значение model_type парсится в enum."""
    obj = HealthDataCreate(**_valid_payload(), model_type="silver")
    assert obj.model_type is ModelTier.SILVER


def test_health_data_create_rejects_unknown_model():
    """Неизвестная модель приводит к ошибке валидации."""
    with pytest.raises(ValidationError):
        HealthDataCreate(**_valid_payload(), model_type="platinum")


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", -1),
        ("age", 200),
        ("gender", 0),
        ("gender", 5),
        ("height", 10),
        ("ap_hi", 10),
        ("ap_lo", 500),
        ("cholesterol", 0),
        ("gluc", 9),
        ("smoke", 2),
        ("alco", -1),
    ],
)
def test_health_data_create_field_bounds(field, value):
    """Все поля валидируются по заданным границам."""
    with pytest.raises(ValidationError):
        HealthDataCreate(**_valid_payload(**{field: value}))
