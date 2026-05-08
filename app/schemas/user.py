from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Базовая модель пользователя."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Уникальное имя пользователя"
    )
    email: EmailStr = Field(..., description="Электронная почта пользователя")


class UserCreate(UserBase):
    """Модель для создания пользователя."""

    password: str = Field(..., min_length=8, max_length=64, description="Пароль в открытом виде")


class UserRead(UserBase):
    """Модель для чтения данных пользователя."""

    id: int = Field(..., description="Уникальный идентификатор пользователя")
    balance: float = Field(..., description="Баланс пользователя")
    loyalty_level_id: int = Field(..., description="Уровень лояльности пользователя")
    role: UserRole = Field(..., description="Роль пользователя")

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Схема для возврата токена после входа."""

    access_token: str = Field(..., description="Токен доступа")
    token_type: str = Field(..., description="Тип токена")


class TokenData(BaseModel):
    """Схема для данных, хранящихся ВНУТРИ токена."""

    username: str | None = Field(None, description="Имя пользователя")
