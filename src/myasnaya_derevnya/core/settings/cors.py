from pydantic_settings import BaseSettings, SettingsConfigDict


class CorsSettings(BaseSettings):
    cors_origins: list[str] = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(extra="ignore")
