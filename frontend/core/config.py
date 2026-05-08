import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LoyaltyTier:
    """Информация об уровне лояльности."""

    name: str
    rank: int
    discount_percent: int
    min_spend: int
    model_label: str
    model_tier: str


LOYALTY_TIERS: tuple[LoyaltyTier, ...] = (
    LoyaltyTier("Bronze", 1, 0, 0, "🟢 Logistic Regression", "bronze"),
    LoyaltyTier("Silver", 2, 5, 500, "🔵 XGBoost", "silver"),
    LoyaltyTier("Gold", 3, 10, 1000, "🟡 Voting Ensemble", "gold"),
)

TIER_BY_NAME = {t.name: t for t in LOYALTY_TIERS}
TIER_BY_MODEL = {t.model_tier: t for t in LOYALTY_TIERS}


class Settings:
    """Настройки фронтенда."""

    API_URL: str = os.getenv("API_URL", "http://localhost:8000/api")
    REQUEST_TIMEOUT: float = float(os.getenv("API_TIMEOUT", "10"))
    PREDICT_POLL_TIMEOUT: int = int(os.getenv("PREDICT_POLL_TIMEOUT", "15"))
    PREDICT_POLL_INTERVAL: float = float(os.getenv("PREDICT_POLL_INTERVAL", "1.0"))


settings = Settings()
