from myasnaya_derevnya.core.settings.base import Settings
from myasnaya_derevnya.core.settings.database import DatabaseSettings


class AppSettings(
    Settings,
    DatabaseSettings,
):
    pass


settings = AppSettings() # type: ignore
