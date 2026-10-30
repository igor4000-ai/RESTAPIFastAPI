# Сервис объявлений купли/продажи

REST API для объявлений купли/продажи на **FastAPI** с базой данных **PostgreSQL**, готовый к запуску в Docker.

## Возможности

- Создание, частичное обновление (PATCH), удаление и получение объявлений по id
- Поиск по любым полям с пагинацией и сортировкой
- Валидация входных данных (Pydantic v2)
- Интерактивная документация: Swagger UI (`/docs`) и ReDoc (`/redoc`)
- Полностью асинхронный доступ к БД (SQLAlchemy 2.0 + asyncpg)

## Структура проекта

```
advertisement-service/
├── app/
│   ├── main.py                  # Точка входа: FastAPI-приложение, lifespan
│   ├── config.py                # Настройки из переменных окружения
│   ├── db.py                    # Движок БД, сессии, зависимость get_db
│   ├── models.py                # ORM-модель Advertisement
│   ├── schemas.py               # Pydantic-схемы (валидация и ответы)
│   └── routers/
│       └── advertisements.py    # Все эндпоинты /advertisement
├── docker-compose.yml           # app + PostgreSQL 16
├── Dockerfile
├── requirements.txt
├── .env.example                 # Пример файла с переменными окружения
└── README.md
```

## Быстрый старт (Docker)

```bash
docker compose up --build
```

Поднимаются два сервиса:

| Сервис | Описание | Адрес |
|---|---|---|
| `app` | Сервис объявлений | http://localhost:8000 (документация: http://localhost:8000/docs) |
| `db` | PostgreSQL 16, данные в volume `postgres_data` | localhost:5432 (только для отладки через psql) |

Остановка: `docker compose down`. С удалением данных: `docker compose down -v`.

## Модель объявления

| Поле | Тип в БД | Ограничения |
|---|---|---|
| `id` | integer, PK | автоинкремент |
| `title` | varchar(255) | обязательное, 1–255 символов |
| `description` | text | необязательное (`null` по умолчанию) |
| `price` | numeric(12,2) | обязательное, 0 … 9 999 999 999.99 |
| `author` | varchar(255) | обязательное, 1–255 символов |
| `created_at` | timestamptz | проставляется базой автоматически при создании |

## API

### 1. Создание — `POST /advertisement`

```bash
curl -X POST http://localhost:8000/advertisement \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Продам велосипед",
    "description": "Городской, алюминиевая рама, состояние отличное",
    "price": 15000,
    "author": "Иван"
  }'
```

Ответ — `201 Created`:

```json
{
  "id": 1,
  "title": "Продам велосипед",
  "description": "Городской, алюминиевая рама, состояние отличное",
  "price": 15000.0,
  "author": "Иван",
  "created_at": "2026-10-30T12:00:00.123456Z"
}
```

### 2. Получение по id — `GET /advertisement/{advertisement_id}`

```bash
curl http://localhost:8000/advertisement/1
```

`200 OK` с объектом либо `404 Not Found`.

### 3. Обновление — `PATCH /advertisement/{advertisement_id}`

Обновляются только переданные поля:

```bash
curl -X PATCH http://localhost:8000/advertisement/1 \
  -H "Content-Type: application/json" \
  -d '{"price": 13500}'
```

- очистить описание: `{"description": null}`
- пустой JSON `{}` → `400 Bad Request`
- несуществующий id → `404 Not Found`

### 4. Удаление — `DELETE /advertisement/{advertisement_id}`

```bash
curl -X DELETE http://localhost:8000/advertisement/1
```

`204 No Content` при успехе, `404 Not Found` — если объявления нет.

### 5. Поиск — `GET /advertisement?{query_string}`

Все параметры необязательны и комбинируются (условия объединяются через `AND`):

| Параметр | Пример | Описание |
|---|---|---|
| `title` | `?title=велосипед` | частичное совпадение заголовка, без учёта регистра |
| `description` | `?description=рама` | частичное совпадение описания |
| `author` | `?author=Иван` | частичное совпадение автора |
| `price_min` | `?price_min=10000` | цена не меньше указанной |
| `price_max` | `?price_max=20000` | цена не больше указанной |
| `created_after` | `?created_after=2026-01-01T00:00:00Z` | создано после даты (ISO 8601) |
| `created_before` | `?created_before=2026-12-31T23:59:59Z` | создано до даты (ISO 8601) |
| `sort_by` | `?sort_by=price` | поле сортировки: `created_at` (по умолчанию), `price`, `id` |
| `order` | `?order=asc` | направление: `asc` / `desc` (по умолчанию `desc`) |
| `limit` | `?limit=20` | размер страницы: 1–100 (по умолчанию 50) |
| `offset` | `?offset=20` | смещение для пагинации |

Примеры:

```bash
# Поиск по заголовку (кириллицу в URL удобно передавать через --data-urlencode)
curl -G http://localhost:8000/advertisement --data-urlencode "title=велосипед"

# Диапазон цен + сортировка по возрастанию
curl "http://localhost:8000/advertisement?price_min=10000&price_max=20000&sort_by=price&order=asc"

# Объявления конкретного автора за период
curl -G http://localhost:8000/advertisement \
  --data-urlencode "author=Иван" \
  --data-urlencode "created_after=2026-10-01T00:00:00Z"
```

Ответ — `200 OK` со списком объявлений (пустой список, если ничего не найдено).

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/advertisements` | строка подключения в формате SQLAlchemy |
| `ECHO_SQL` | `false` | печатать SQL-запросы в лог (отладка) |

## Локальный запуск без Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Нужен запущенный PostgreSQL; создайте базу:
#   CREATE DATABASE advertisements;
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/advertisements"

uvicorn app.main:app --reload
```

## Детали реализации

- **Асинхронность**: FastAPI + SQLAlchemy 2.0 (async) + asyncpg — ни одного блокирующего вызова на пути запроса.
- **Схема БД**: таблицы создаются автоматически при старте, с повторными попытками подключения (PostgreSQL в compose может подниматься дольше приложения). Для продакшена рекомендуются Alembic-миграции.
- **Поиск**: `ILIKE` для текстовых полей — регистронезависимый поиск, включая кириллицу; спецсимволы `%` и `_` экранируются.
- **Ошибки**: `404` — объявление не найдено; `400` — некорректные фильтры (`price_min > price_max`) или пустой PATCH; `422` — ошибки валидации полей.
