from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class BaseAppSettings(BaseSettings):
    """Общая основа настроек: все группы читают один проектный `.env`.

    Путь абсолютный (``PROJECT_ROOT``), а не относительный: иначе он зависел бы
    от текущей рабочей директории процесса.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Settings(BaseAppSettings):
    debug: bool
