import logging
import sys

from myasnaya_derevnya.core.logging.filters import ContextFilter
from myasnaya_derevnya.core.logging.formatters import ConsoleFormatter, JsonFormatter
from myasnaya_derevnya.core.settings.logging import LoggingSettings

HANDLER_NAME = "myasnaya_derevnya"

# Чужие логгеры, которые при root=INFO засоряют вывод.
_QUIET_LOGGERS = {
    # INFO-строка на каждый исходящий запрос; свои запросы логируем явно.
    "httpx": logging.WARNING,
    # Access-лог пишем сами в middleware, чтобы не дублировать строки uvicorn.
    "uvicorn.access": logging.WARNING,
}

_handler: logging.Handler | None = None


def setup_logging(settings: LoggingSettings) -> None:
    """Настраивает корневой логгер приложения.

    Идемпотентна: при повторном вызове заменяет только собственный хендлер и не
    трогает чужие (например, перехватчик логов в тестах). Пишем в stdout —
    файлы и ротацию оставляем процессному менеджеру.
    """
    global _handler

    root = logging.getLogger()
    if _handler is not None:
        root.removeHandler(_handler)
        _handler.close()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.name = HANDLER_NAME
    handler.setFormatter(JsonFormatter() if settings.log_json else ConsoleFormatter())
    handler.addFilter(ContextFilter())

    _handler = handler
    root.addHandler(handler)
    root.setLevel(_normalize_level(settings.log_level))

    for name, level in _QUIET_LOGGERS.items():
        logging.getLogger(name).setLevel(level)


def _normalize_level(level: str) -> int:
    value = logging.getLevelNamesMapping().get(level.upper())
    if value is None:
        raise ValueError(f"Неизвестный уровень логирования: {level!r}")
    return value
