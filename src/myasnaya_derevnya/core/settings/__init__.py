from pathlib import Path

from pydantic_settings import SettingsConfigDict

from myasnaya_derevnya.core.settings.base import Settings
from myasnaya_derevnya.core.settings.database import DatabaseSettings
from myasnaya_derevnya.core.settings.login_codes import LoginCodeSettings
from myasnaya_derevnya.core.settings.seed import InitSeedSettings

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class AppSettings(Settings, DatabaseSettings, InitSeedSettings, LoginCodeSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AppSettings()  # type: ignore
