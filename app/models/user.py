import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimeStampMixin

if TYPE_CHECKING:
    from app.models.loyalty_level import LoyaltyLevel
    from app.models.prediction import Prediction
    from app.models.transaction import Transaction


class UserRole(enum.StrEnum):
    """Роли пользователей."""

    USER = "user"
    ADMIN = "admin"


class User(Base, TimeStampMixin):
    """Пользователи сервиса."""

    __tablename__ = "users"

    __table_args__ = (CheckConstraint("balance >= 0", name="check_balance_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="userrole",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )

    loyalty_level_id: Mapped[int] = mapped_column(ForeignKey("loyalty_levels.id"), default=1)

    loyalty_level: Mapped["LoyaltyLevel"] = relationship(back_populates="users")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
