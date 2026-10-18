import json
import logging

from myasnaya_derevnya.core.logging.formatters import ConsoleFormatter, JsonFormatter


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="myasnaya_derevnya.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Привет, %s",
        args=("мир",),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_message_and_context() -> None:
    payload = json.loads(JsonFormatter().format(_record(request_id="req-1")))

    assert payload["message"] == "Привет, мир"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "myasnaya_derevnya.test"
    assert payload["request_id"] == "req-1"


def test_json_formatter_omits_absent_request_id() -> None:
    payload = json.loads(JsonFormatter().format(_record()))

    assert "request_id" not in payload


def test_json_formatter_includes_extra_fields() -> None:
    payload = json.loads(
        JsonFormatter().format(_record(order_id="o-1", user_id="u-1"))
    )

    assert payload["order_id"] == "o-1"
    assert payload["user_id"] == "u-1"


def test_console_formatter_renders_extra_fields() -> None:
    line = ConsoleFormatter().format(_record(order_id="o-1"))

    assert "order_id=o-1" in line
    assert "Привет, мир" in line


def test_console_formatter_shows_short_request_id() -> None:
    line = ConsoleFormatter().format(_record(request_id="abcdef1234567890"))

    assert "[abcdef12]" in line
    assert "Привет, мир" in line
