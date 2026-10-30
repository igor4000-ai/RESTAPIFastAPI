"""Точка входа: создание FastAPI-приложения."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import Base, engine
from app.routers import advertisements

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

# Сколько раз и с каким интервалом пытаться создать таблицы при старте:
# PostgreSQL в docker compose может подниматься дольше, чем приложение
DB_INIT_RETRIES = 10
DB_INIT_RETRY_DELAY = 2.0


async def init_db() -> None:
    """Создаёт таблицы при старте (если их ещё нет).

    Для учебных и демонстрационных задач достаточно create_all;
    в продакшене правильнее использовать Alembic-миграции.
    """
    for attempt in range(1, DB_INIT_RETRIES + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception:  # БД может быть ещё недоступна — пробуем снова
            if attempt == DB_INIT_RETRIES:
                raise
            logger.warning(
                "База данных недоступна (попытка %d/%d), повтор через %.1f с…",
                attempt,
                DB_INIT_RETRIES,
                DB_INIT_RETRY_DELAY,
            )
            await asyncio.sleep(DB_INIT_RETRY_DELAY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Подготовка ресурсов при старте и освобождение при остановке."""
    await init_db()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "REST API для объявлений купли/продажи: "
        "создание, частичное обновление, удаление, получение по id "
        "и поиск по полям с пагинацией и сортировкой."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(advertisements.router)


@app.get("/health", tags=["Служебные"], summary="Проверка готовности сервиса")
async def health() -> dict[str, str]:
    """Эндпоинт для healthcheck: используется docker compose и балансировщиками."""
    return {"status": "ok"}
