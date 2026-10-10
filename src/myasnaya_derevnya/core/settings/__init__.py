from pathlib import Path

from pydantic_settings import SettingsConfigDict

from myasnaya_derevnya.core.settings.base import Settings
from myasnaya_derevnya.core.settings.database import DatabaseSettings
from myasnaya_derevnya.core.settings.seed import InitSeedSettings

# .../src/myasnaya_derevnya/core/settings/__init__.py
# parents: settings -> core -> myasnaya_derevnya -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]


class AppSettings(Settings, DatabaseSettings, InitSeedSettings):
    # env_file задаётся здесь, а не в базовом Settings: при множественном
    # наследовании настройки баз перетираются и env_file теряется.
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AppSettings()  # type: ignore
