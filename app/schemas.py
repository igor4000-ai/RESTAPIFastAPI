"""Pydantic-схемы: валидация входных данных и формат ответов API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

MAX_TEXT_LENGTH = 255
MAX_PRICE = Decimal("9999999999.99")  # максимум для numeric(12, 2)


class AdvertisementCreate(BaseModel):
    """Данные для создания объявления."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Заголовок объявления",
        examples=["Продам велосипед"],
    )
    description: str | None = Field(
        default=None,
        description="Описание товара (необязательное)",
        examples=["Городской, алюминиевая рама, состояние отличное"],
    )
    price: Decimal = Field(
        ...,
        ge=0,
        le=MAX_PRICE,
        description="Цена (0 — «бесплатно»)",
        examples=[15000.00],
    )
    author: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Автор объявления",
        examples=["Иван"],
    )


class AdvertisementUpdate(BaseModel):
    """Данные для частичного обновления (PATCH).

    Все поля необязательные — обновятся только явно переданные.
    Чтобы очистить описание, передайте "description": null.
    """

    title: str | None = Field(default=None, min_length=1, max_length=MAX_TEXT_LENGTH)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, le=MAX_PRICE)
    author: str | None = Field(default=None, min_length=1, max_length=MAX_TEXT_LENGTH)


class AdvertisementResponse(AdvertisementCreate):
    """Представление объявления в ответах API."""

    id: int = Field(description="Уникальный идентификатор")
    created_at: datetime = Field(description="Дата и время создания (UTC)")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("price")
    def _serialize_price(self, value: Decimal) -> float:
        """Отдаём цену JSON-числом.

        Внутри БД цена хранится точно (numeric(12,2)); float используется
        только на границе API, чтобы клиенту приходило число, а не строка.
        """
        return float(value)
