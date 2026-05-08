import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.loyalty_level import LoyaltyLevel
from app.models.user import User, UserRole


async def seed_loyalty_levels(session) -> None:
    """Создаёт базовые уровни лояльности, если их ещё нет."""
    result = await session.execute(select(LoyaltyLevel))
    if result.scalars().first():
        print("Loyalty levels уже существуют. Пропускаем.")
        return
    session.add_all(
        [
            LoyaltyLevel(name="Bronze", discount_rate=0.0, min_spend=0.0),
            LoyaltyLevel(name="Silver", discount_rate=0.05, min_spend=100.0),
            LoyaltyLevel(name="Gold", discount_rate=0.1, min_spend=500.0),
        ]
    )
    await session.commit()
    print("Loyalty levels успешно добавились в базу данных.")


async def seed_admin(session) -> None:
    """Создаёт администратора из переменных окружения, если он ещё не существует."""
    if not (settings.ADMIN_USERNAME and settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD):
        print("Admin credentials не заданы - пропускаем.")
        return
    result = await session.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
    if result.scalars().first():
        print(f"Admin {settings.ADMIN_USERNAME} уже существует - пропускаем.")
        return
    bronze_res = await session.execute(select(LoyaltyLevel).where(LoyaltyLevel.name == "Bronze"))
    bronze = bronze_res.scalar_one()
    session.add(
        User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            loyalty_level_id=bronze.id,
        )
    )
    await session.commit()
    print(f"Admin {settings.ADMIN_USERNAME} создан.")


async def main() -> None:
    """Запускает все сидеры в одной сессии."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        await seed_loyalty_levels(session)
        await seed_admin(session)


if __name__ == "__main__":
    asyncio.run(main())
