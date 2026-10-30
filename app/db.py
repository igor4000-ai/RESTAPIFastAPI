"""Подключение к базе данных и базовые зависимости."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.echo_sql,
    # Проверять соединение перед использованием — помогает после рестарта БД
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: выдаёт сессию БД на время запроса."""
    async with AsyncSessionLocal() as session:
        yield session
