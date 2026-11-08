from datetime import date, datetime
from zoneinfo import ZoneInfo

from myasnaya_derevnya.core.settings import settings


def company_timezone() -> ZoneInfo:
    """Часовой пояс компании из настроек."""

    return ZoneInfo(settings.timezone)


def to_company_time(value: datetime) -> datetime:
    """Переводит момент времени в часовой пояс компании."""

    if value.tzinfo is None:
        raise ValueError("Ожидается время с часовым поясом")

    return value.astimezone(company_timezone())


def company_date(value: datetime) -> date:
    """Календарная дата момента времени в часовом поясе компании."""

    return to_company_time(value).date()


def company_today() -> date:
    """Сегодняшняя дата в часовом поясе компании."""

    return datetime.now(company_timezone()).date()
