import json
import logging
from datetime import UTC, datetime

REQUEST_ID_SHORT_LENGTH = 8

# Атрибуты, которые logging кладёт в запись сам. Всё остальное — наши поля
# из ``extra=`` и ``ContextFilter``; их и выводим.
_RESERVED_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"asctime", "message", "taskName"}


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED_ATTRS and not key.startswith("_")
    }


class ConsoleFormatter(logging.Formatter):
    """Человекочитаемый формат для локальной разработки."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        head = f"{timestamp} {record.levelname:<7} {record.name}"

        extras = _extra_fields(record)
        request_id = extras.pop("request_id", None)
        if request_id:
            head += f" [{str(request_id)[:REQUEST_ID_SHORT_LENGTH]}]"

        line = f"{head} {record.getMessage()}"
        if extras:
            line += " " + " ".join(f"{key}={value}" for key, value in extras.items())
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


class JsonFormatter(logging.Formatter):
    """Машиночитаемый формат для прода."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_extra_fields(record))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)
