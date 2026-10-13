from pydantic_settings import BaseSettings, SettingsConfigDict


class LoginCodeSettings(BaseSettings):
    login_code_secret: str = "dev-secret-change-me"
    login_code_length: int = 6
    login_code_ttl_seconds: int = 300
    login_code_max_attempts: int = 5
    login_code_min_interval_seconds: int = 60
    login_code_hourly_limit: int = 5

    model_config = SettingsConfigDict(extra="ignore")
