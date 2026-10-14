from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_LENGTH = 16


class LoginCodeSettings(BaseSettings):
    login_code_secret: str = Field(min_length=MIN_SECRET_LENGTH)
    login_code_length: int = 6
    login_code_ttl_seconds: int = 300
    login_code_max_attempts: int = 5
    login_code_min_interval_seconds: int = 60
    login_code_hourly_limit: int = 5

    model_config = SettingsConfigDict(extra="ignore")
