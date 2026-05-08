import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimeStampMixin

if TYPE_CHECKING:
    from app.models.user import User


class TransactionType(enum.StrEnum):
    """Типы транзакций пользователя."""

    REFILL = "refill"
    PAYMENT = "payment"
    REFUND = "refund"


class Transaction(Base, TimeStampMixin):
    """Транзакции пользователя."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_transactions_user_challenge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    challenge_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="transactions")
