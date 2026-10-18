import logging

import pytest
from starlette.requests import Request

from myasnaya_derevnya.core.logging.filters import ContextFilter
from myasnaya_derevnya.main import unhandled_error_handler


def _request(request_id: str) -> Request:
    return Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "query_string": b"",
            "headers": [],
            "scheme": "http",
            "server": ("test", 80),
            "request_id": request_id,
        }
    )


async def test_unhandled_error_handler_returns_generic_500(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.handler.addFilter(ContextFilter())

    with caplog.at_level(logging.ERROR, logger="myasnaya_derevnya.main"):
        response = await unhandled_error_handler(_request("req-9"), RuntimeError("boom"))

    assert response.status_code == 500
    assert response.body == b'{"message":"Internal server error"}'
    assert any(getattr(r, "request_id", None) == "req-9" for r in caplog.records)
