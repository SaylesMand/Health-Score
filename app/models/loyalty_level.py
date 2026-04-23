from typing import TYPE_CHECKING

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class LoyaltyLevel(Base):
    """Уровни лояльности пользователей."""

    __tablename__ = "loyalty_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_rate: Mapped[float] = mapped_column(Float, default=0.0)
    min_spend: Mapped[float] = mapped_column(Float, default=0.0)

    users: Mapped[list["User"]] = relationship(back_populates="loyalty_level")
