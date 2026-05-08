from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки проекта."""

    PROJECT_NAME: str = "Health Score API"
    PROJECT_VERSION: str = "0.1.0"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    SECRET_KEY: str = Field(..., min_length=16, description="JWT secret. Минимум 16 символов.")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    ALLOWED_ORIGINS: str = "http://localhost:8501,http://localhost:3000"

    LOYALTY_RECALC_DEBUG: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """Строка подключения к базе данных."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins(self) -> list[str]:
        """Список разрешенных источников."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
