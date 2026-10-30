"""Настройки приложения.

Значения по умолчанию можно переопределить через переменные окружения
или файл .env (пример — в .env.example).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки, которые читаются из окружения при старте приложения."""

    app_name: str = "Сервис объявлений купли/продажи"

    # Строка подключения в формате SQLAlchemy:
    # postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/advertisements"

    # Показывать SQL-запросы в логах (полезно при отладке)
    echo_sql: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
