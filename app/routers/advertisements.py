"""Эндпоинты для работы с объявлениями."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.db import get_db

router = APIRouter(prefix="/advertisement", tags=["Объявления"])

NOT_FOUND_DETAIL = "Объявление не найдено"


def _ilike_pattern(value: str) -> str:
    """Экранирует спецсимволы LIKE (%, _) и оборачивает значение в «%…%».

    Благодаря экранированию поиск «100%» находит буквальную строку,
    а не работает как маска.
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def _get_or_404(advertisement_id: int, db: AsyncSession) -> models.Advertisement:
    """Возвращает объявление по id или бросает 404 Not Found."""
    advertisement = await db.get(models.Advertisement, advertisement_id)
    if advertisement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_DETAIL,
        )
    return advertisement


@router.post(
    "",
    response_model=schemas.AdvertisementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать объявление",
)
async def create_advertisement(
    payload: schemas.AdvertisementCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.AdvertisementResponse:
    """Создаёт новое объявление и возвращает его с присвоенным **id** и датой создания."""
    advertisement = models.Advertisement(**payload.model_dump())
    db.add(advertisement)
    await db.commit()
    await db.refresh(advertisement)
    return advertisement


@router.get(
    "",
    response_model=list[schemas.AdvertisementResponse],
    summary="Поиск объявлений по полям",
)
async def search_advertisements(
    db: Annotated[AsyncSession, Depends(get_db)],
    title: Annotated[
        str | None,
        Query(description="Частичное совпадение заголовка, без учёта регистра"),
    ] = None,
    description: Annotated[
        str | None,
        Query(description="Частичное совпадение описания, без учёта регистра"),
    ] = None,
    author: Annotated[
        str | None,
        Query(description="Частичное совпадение автора, без учёта регистра"),
    ] = None,
    price_min: Annotated[
        Decimal | None,
        Query(ge=0, description="Цена не меньше указанной (включительно)"),
    ] = None,
    price_max: Annotated[
        Decimal | None,
        Query(ge=0, description="Цена не больше указанной (включительно)"),
    ] = None,
    created_after: Annotated[
        datetime | None,
        Query(description="Создано после этой даты (ISO 8601, например 2026-01-01T00:00:00Z)"),
    ] = None,
    created_before: Annotated[
        datetime | None,
        Query(description="Создано до этой даты (ISO 8601)"),
    ] = None,
    sort_by: Annotated[
        Literal["created_at", "price", "id"],
        Query(description="Поле сортировки"),
    ] = "created_at",
    order: Annotated[
        Literal["asc", "desc"],
        Query(description="Направление сортировки"),
    ] = "desc",
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Максимум объявлений в ответе"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Смещение (для пагинации)"),
    ] = 0,
) -> list[schemas.AdvertisementResponse]:
    """Возвращает объявления, отфильтрованные по переданным параметрам.

    Все фильтры необязательны и комбинируются (условия объединяются через AND).
    Без параметров возвращаются все объявления — свежие сверху.
    """
    if price_min is not None and price_max is not None and price_min > price_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_min не может быть больше price_max",
        )

    query = select(models.Advertisement)

    if title is not None:
        query = query.where(
            models.Advertisement.title.ilike(_ilike_pattern(title), escape="\\"),
        )
    if description is not None:
        query = query.where(
            models.Advertisement.description.ilike(_ilike_pattern(description), escape="\\"),
        )
    if author is not None:
        query = query.where(
            models.Advertisement.author.ilike(_ilike_pattern(author), escape="\\"),
        )
    if price_min is not None:
        query = query.where(models.Advertisement.price >= price_min)
    if price_max is not None:
        query = query.where(models.Advertisement.price <= price_max)
    if created_after is not None:
        query = query.where(models.Advertisement.created_at >= created_after)
    if created_before is not None:
        query = query.where(models.Advertisement.created_at <= created_before)

    # Вторичный ключ сортировки — стабильный порядок при пагинации
    sort_column = getattr(models.Advertisement, sort_by)
    direction = sort_column.desc() if order == "desc" else sort_column.asc()
    query = query.order_by(direction, models.Advertisement.id.asc())

    result = await db.execute(query.limit(limit).offset(offset))
    return list(result.scalars().all())


@router.get(
    "/{advertisement_id}",
    response_model=schemas.AdvertisementResponse,
    summary="Получить объявление по id",
)
async def get_advertisement(
    advertisement_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.AdvertisementResponse:
    """Возвращает объявление по его идентификатору."""
    return await _get_or_404(advertisement_id, db)


@router.patch(
    "/{advertisement_id}",
    response_model=schemas.AdvertisementResponse,
    summary="Частично обновить объявление",
)
async def update_advertisement(
    advertisement_id: int,
    payload: schemas.AdvertisementUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.AdvertisementResponse:
    """Обновляет только переданные поля, остальные остаются без изменений.

    Пример: `{"price": 12500}` — изменит цену, заголовок и автор не тронет.
    """
    advertisement = await _get_or_404(advertisement_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не передано ни одного поля для обновления",
        )

    for field, value in update_data.items():
        setattr(advertisement, field, value)

    await db.commit()
    await db.refresh(advertisement)
    return advertisement


@router.delete(
    "/{advertisement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить объявление",
)
async def delete_advertisement(
    advertisement_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Удаляет объявление. При успехе — 204 No Content, при отсутствии — 404."""
    advertisement = await _get_or_404(advertisement_id, db)
    await db.delete(advertisement)
    await db.commit()
