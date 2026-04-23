from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.loyalty_level import LoyaltyLevel
from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    """Репозиторий для работы с пользователями в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_in: UserCreate) -> User:
        """Создает нового пользователя с базовым уровнем лояльности."""
        query = select(LoyaltyLevel).where(LoyaltyLevel.name == "Bronze")
        result = await self.session.execute(query)
        loyalty_level = result.scalar_one_or_none()
        if not loyalty_level:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Базовый уровень лояльности не найден.",
            )

        hashed_pwd = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_pwd,
            loyalty_level_id=loyalty_level.id,
        )
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user

    async def get_by_id(self, user_id: int) -> User | None:
        """Получает пользователя по ID."""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Получает пользователя по адресу электронной почты."""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Получает пользователя по имени пользователя."""
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
