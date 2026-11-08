from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator

from myasnaya_derevnya.core.settings.base import BaseAppSettings


class TimezoneSettings(BaseAppSettings):
    """Часовой пояс компании для отчётов и нумерации документов."""

    timezone: str = "Europe/Moscow"

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Неизвестный часовой пояс: {value}") from exc

        return value
