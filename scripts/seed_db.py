import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.loyalty_level import LoyaltyLevel


async def seed_loyalty_levels():
    """С уровней лояльности в базу данных."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(LoyaltyLevel))
        if result.scalars().first():
            print("Loyalty levels уже существуют. Пропускаем.")
            return

        levels = [
            LoyaltyLevel(name="Bronze", discount_rate=0.0, min_spend=0.0),
            LoyaltyLevel(name="Silver", discount_rate=0.05, min_spend=100.0),
            LoyaltyLevel(name="Gold", discount_rate=0.1, min_spend=500.0),
        ]
        session.add_all(levels)
        await session.commit()
        print("Loyalty levels успешено добавились в базу данных.")


if __name__ == "__main__":
    asyncio.run(seed_loyalty_levels())
