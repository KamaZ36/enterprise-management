import logging

import httpx
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from myasnaya_derevnya.core.logging.filters import ContextFilter
from myasnaya_derevnya.core.logging.middleware import RequestContextMiddleware

ACCESS_LOGGER = "myasnaya_derevnya.access"


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


async def _endpoint(request: object) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _app(path: str = "/items/{item_id}") -> Starlette:
    app = Starlette(routes=[Route(path, _endpoint)])
    app.add_middleware(RequestContextMiddleware)
    return app


def _client(app: Starlette) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


class _capture:
    """Временный хендлер на access-логгере, чтобы поймать строки доступа."""

    def __enter__(self) -> list[logging.LogRecord]:
        self._logger = logging.getLogger(ACCESS_LOGGER)
        self._level = self._logger.level
        self._propagate = self._logger.propagate
        self._handler = _CaptureHandler()
        self._handler.addFilter(ContextFilter())
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._logger.addHandler(self._handler)
        return self._handler.records

    def __exit__(self, *exc: object) -> None:
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._level)
        self._logger.propagate = self._propagate


async def test_access_log_carries_request_id_and_route() -> None:
    with _capture() as records:
        async with _client(_app()) as client:
            response = await client.get("/items/42")

    request_id = response.headers["x-request-id"]
    assert request_id

    assert len(records) == 1
    record = records[0]
    assert record.request_id == request_id
    assert "/items/{item_id}" in record.getMessage()
    assert "-> 200" in record.getMessage()


async def test_client_request_id_is_reused() -> None:
    async with _client(_app()) as client:
        response = await client.get("/items/1", headers={"X-Request-ID": "given-id"})

    assert response.headers["x-request-id"] == "given-id"


async def test_skipped_paths_are_not_logged() -> None:
    with _capture() as records:
        async with _client(_app("/docs")) as client:
            await client.get("/docs")

    assert records == []
