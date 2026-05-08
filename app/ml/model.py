import logging
import os

import joblib
import pandas as pd

logger = logging.getLogger(__name__)


class ModelWrapper:
    """Синглтон для ленивой загрузки ML моделей."""

    _instance = None
    _models = {}

    def __new__(cls):
        """Создает или возвращает экземпляр класса."""
        if cls._instance is None:
            cls._instance = super(ModelWrapper, cls).__new__(cls)
            cls._instance._models = {}
        return cls._instance

    def load_models(self) -> None:
        """Загружает модели с диска."""
        if self._models:
            return

        base_path = os.path.join(os.path.dirname(__file__), "models")
        models_to_load = {
            "bronze": "logreg.pkl",
            "silver": "xgb.pkl",
            "gold": "voting_soft.pkl",
        }

        for level, filename in models_to_load.items():
            path = os.path.join(base_path, filename)
            if os.path.exists(path):
                try:
                    self._models[level] = joblib.load(path)
                    logger.info(f"Модель для {level} загружена: {filename}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки {filename}: {e}")
            else:
                logger.error(f"Критическая ошибка: Файл модели не найден: {path}")

    def _engineer_features(self, data: dict) -> pd.DataFrame:
        """Подготовка признаков (Feature Engineering) строго как в ноутбуке."""  # https://www.kaggle.com/code/vbmokin/20-models-for-cardiovascular-disease-prediction
        age_days = int(data["age"] * 365.25)

        weight = data["weight"]
        height = data["height"]

        bmi = weight / ((height / 100.0) ** 2) if height > 0 else 0

        features_dict = {
            "age": [age_days],
            "gender": [data["gender"]],
            "height": [height],
            "weight": [weight],
            "ap_hi": [data["ap_hi"]],
            "ap_lo": [data["ap_lo"]],
            "cholesterol": [data["cholesterol"]],
            "gluc": [data["gluc"]],
            "smoke": [data["smoke"]],
            "alco": [data["alco"]],
            "active": [data["active"]],
            "bmi": [bmi],
        }
        return pd.DataFrame(features_dict)

    def predict_probability(self, data: dict, loyalty_level_name: str) -> float:
        """Предсказание вероятности (0.0 - 1.0) с использованием нужной модели."""
        if not self._models:
            self.load_models()

        level = loyalty_level_name.lower()
        model = self._models.get(level) or self._models.get("bronze")

        if not model:
            raise RuntimeError("ML Модели не загружены. Инференс невозможен.")

        features_df = self._engineer_features(data)
        prediction = model.predict_proba(features_df)[0][1]
        return round(float(prediction), 4)


ml_model = ModelWrapper()
