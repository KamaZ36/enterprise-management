from pydantic import Field

from myasnaya_derevnya.core.settings.base import BaseAppSettings


class CorsSettings(BaseAppSettings):
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ]
    )
