from pydantic_settings import BaseSettings, SettingsConfigDict


class MediaSettings(BaseSettings):
    media_root: str = "media"
    media_url_prefix: str = "/media"


    media_max_bytes: int = 8 * 1024 * 1024
    media_max_side: int = 1600
    media_webp_quality: int = 82

    model_config = SettingsConfigDict(extra="ignore")
