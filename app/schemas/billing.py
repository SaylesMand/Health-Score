from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionType


class LoyaltyLevelRead(BaseModel):
    """Модель для чтения данных уровня лояльности."""

    id: int = Field(..., description="Уникальный идентификатор уровня лояльности")
    name: str = Field(..., description="Название уровня лояльности")
    discount_percent: float = Field(..., description="Процент скидки")
    threshold_requests: int = Field(..., description="Порог по количеству запросов")

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    """Модель для создания транзакции."""

    amount: float = Field(..., gt=0, description="Сумма должна быть положительной")
    transaction_type: TransactionType = Field(..., description="Тип транзакции")


class TransactionRead(BaseModel):
    """Модель для чтения данных транзакции."""

    id: int = Field(..., description="Уникальный идентификатор транзакции")
    user_id: int = Field(..., description="Идентификатор пользователя")
    amount: float = Field(..., description="Сумма транзакции")
    transaction_type: TransactionType = Field(..., description="Тип транзакции")
    created_at: datetime = Field(..., description="Дата и время создания транзакции")

    model_config = ConfigDict(from_attributes=True)


class RefillRequest(BaseModel):
    """Модель для запроса на пополнение баланса."""

    amount: float = Field(..., gt=0, description="Сумма должна быть положительной")


class RefillResponse(BaseModel):
    """Модель для ответа на запрос на пополнение баланса."""

    message: str = Field(..., description="Сообщение об успешном пополнении")
    new_balance: float = Field(..., description="Новый баланс пользователя")
