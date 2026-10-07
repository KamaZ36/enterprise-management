from myasnaya_derevnya.core.settings.base import Settings
from myasnaya_derevnya.core.settings.database import DatabaseSettings
from myasnaya_derevnya.core.settings.seed import InitSeedSettings


class AppSettings(Settings, DatabaseSettings, InitSeedSettings):
    pass


settings = AppSettings()  # type: ignore
