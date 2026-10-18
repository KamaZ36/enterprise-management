import logging

import pytest

from myasnaya_derevnya.core.logging.config import HANDLER_NAME, setup_logging
from myasnaya_derevnya.core.logging.formatters import ConsoleFormatter, JsonFormatter
from myasnaya_derevnya.core.settings.logging import LoggingSettings


def _our_handlers() -> list[logging.Handler]:
    return [h for h in logging.getLogger().handlers if h.name == HANDLER_NAME]


def test_setup_logging_installs_single_handler() -> None:
    setup_logging(LoggingSettings(log_level="DEBUG", log_json=True))
    setup_logging(LoggingSettings(log_level="DEBUG", log_json=True))

    handlers = _our_handlers()
    assert len(handlers) == 1
    assert isinstance(handlers[0].formatter, JsonFormatter)
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_switches_formatter() -> None:
    setup_logging(LoggingSettings(log_json=False))
    assert isinstance(_our_handlers()[0].formatter, ConsoleFormatter)

    setup_logging(LoggingSettings(log_json=True))
    assert isinstance(_our_handlers()[0].formatter, JsonFormatter)


def test_setup_logging_rejects_unknown_level() -> None:
    with pytest.raises(ValueError):
        setup_logging(LoggingSettings(log_level="nope"))
