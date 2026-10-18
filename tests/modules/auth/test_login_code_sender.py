import logging

import pytest

from myasnaya_derevnya.modules.auth.infrastructure.service.login_code_sender.cli import (
    LoggingLoginCodeSender,
)


async def test_debug_sender_logs_code(caplog: pytest.LogCaptureFixture) -> None:
    sender = LoggingLoginCodeSender(debug=True)

    with caplog.at_level(logging.WARNING):
        await sender.send("+79990000000", "123456")

    assert "123456" in caplog.text


async def test_sender_without_debug_hides_code(caplog: pytest.LogCaptureFixture) -> None:
    sender = LoggingLoginCodeSender(debug=False)

    with caplog.at_level(logging.DEBUG):
        await sender.send("+79990000000", "123456")

    assert "123456" not in caplog.text
    assert "не настроен" in caplog.text
