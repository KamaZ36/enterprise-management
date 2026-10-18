from myasnaya_derevnya.core.settings.base import PROJECT_ROOT, Settings
from myasnaya_derevnya.core.settings.database import DatabaseSettings
from myasnaya_derevnya.core.settings.logging import LoggingSettings
from myasnaya_derevnya.core.settings.login_codes import LoginCodeSettings
from myasnaya_derevnya.core.settings.media import MediaSettings
from myasnaya_derevnya.core.settings.seed import InitSeedSettings


class AppSettings(
    Settings,
    DatabaseSettings,
    InitSeedSettings,
    LoginCodeSettings,
    LoggingSettings,
    MediaSettings,
):
    pass


settings = AppSettings()  # type: ignore
