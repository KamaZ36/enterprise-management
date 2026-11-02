from pydantic import Field

from myasnaya_derevnya.core.settings.base import BaseAppSettings


class PasswordLoginSettings(BaseAppSettings):
    login_max_attempts: int = Field(default=5, ge=1)
    login_attempt_window_seconds: int = Field(default=900, ge=1)
    login_lockout_seconds: int = Field(default=900, ge=1)
