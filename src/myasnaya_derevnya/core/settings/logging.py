from myasnaya_derevnya.core.settings.base import BaseAppSettings


class LoggingSettings(BaseAppSettings):
    log_level: str = "INFO"
    log_json: bool = False
    log_access: bool = True
