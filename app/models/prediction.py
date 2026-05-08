import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimeStampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PredictionStatus(enum.StrEnum):
    """Статусы предсказаний модели."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Prediction(Base, TimeStampMixin):
    """Предсказания модели для пользователя."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[Float | None] = mapped_column(Float, nullable=True)
    status: Mapped[PredictionStatus] = mapped_column(
        Enum(PredictionStatus), default=PredictionStatus.PENDING
    )
    price_charged: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="predictions")
