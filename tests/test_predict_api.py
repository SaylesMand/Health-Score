from unittest.mock import patch

import pytest

from app.ml.model import ml_model


@pytest.fixture
def stub_ml_model(monkeypatch):
    """Подменяет ML-инференс константой, чтобы не грузить модели с диска."""
    monkeypatch.setattr(ml_model, "predict_probability", lambda data, level: 0.42)
    yield


def _payload(model_type: str = "bronze") -> dict:
    """Готовит валидный payload для /predict/predict."""
    return {
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
        "model_type": model_type,
    }


async def test_predict_charges_and_returns_pending(client, registered_user, stub_ml_model):
    """Успешный predict списывает 100 кр и возвращает pending->completed (eager Celery)."""
    await client.post("/api/billing/refill", json={"amount": 200}, headers=registered_user["auth"])

    res = await client.post(
        "/api/predict/predict", json=_payload(), headers=registered_user["auth"]
    )
    assert res.status_code == 200
    assert res.json()["prediction_id"] > 0

    bal = await client.get("/api/billing/balance", headers=registered_user["auth"])
    assert bal.json()["balance"] == 100.0

    history = await client.get("/api/predict/history", headers=registered_user["auth"])
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 1
    assert items[0]["status"] == "completed"
    assert items[0]["probability"] == 0.42


async def test_predict_402_on_insufficient_balance(client, registered_user, stub_ml_model):
    """Без баланса predict возвращает 402."""
    res = await client.post(
        "/api/predict/predict", json=_payload(), headers=registered_user["auth"]
    )
    assert res.status_code == 402


async def test_predict_403_on_unavailable_model(client, registered_user, stub_ml_model):
    """Bronze-юзер не может вызвать Gold-модель: 403."""
    await client.post("/api/billing/refill", json={"amount": 200}, headers=registered_user["auth"])
    res = await client.post(
        "/api/predict/predict",
        json=_payload(model_type="gold"),
        headers=registered_user["auth"],
    )
    assert res.status_code == 403


async def test_predict_503_on_celery_failure_refunds(client, registered_user, stub_ml_model):
    """При сбое постановки в Celery возвращается 503 и происходит refund."""
    await client.post("/api/billing/refill", json={"amount": 200}, headers=registered_user["auth"])

    with patch(
        "app.api.endpoints.predict.compute_health_prediction.delay",
        side_effect=RuntimeError("broker down"),
    ):
        res = await client.post(
            "/api/predict/predict", json=_payload(), headers=registered_user["auth"]
        )
    assert res.status_code == 503

    bal = await client.get("/api/billing/balance", headers=registered_user["auth"])
    assert bal.json()["balance"] == 200.0
