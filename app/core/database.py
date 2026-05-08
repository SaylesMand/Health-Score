from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Получает объект сессии базы данных."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
