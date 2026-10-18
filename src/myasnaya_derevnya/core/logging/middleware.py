import logging
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from myasnaya_derevnya.core.logging.context import (
    reset_request_id,
    set_request_id,
    set_user_id,
)

logger = logging.getLogger("myasnaya_derevnya.access")

REQUEST_ID_HEADER = b"x-request-id"
MAX_REQUEST_ID_LENGTH = 64
SKIPPED_PATH_PREFIXES = ("/media", "/docs", "/redoc", "/openapi.json")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        token = set_request_id(request_id)
        # Дублируем в scope: обработчик необработанных ошибок живёт снаружи
        # middleware, где contextvar уже сброшен.
        scope["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"].append(
                    (REQUEST_ID_HEADER, request_id.encode("latin-1"))
                )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if self.enabled and not scope["path"].startswith(SKIPPED_PATH_PREFIXES):
                logger.info(
                    "%s %s %s -> %s (%.2f ms)",
                    _client(scope),
                    scope["method"],
                    _route(scope),
                    status_code,
                    (time.perf_counter() - started) * 1000,
                )
            reset_request_id(token)
            set_user_id(None)


def _request_id(scope: Scope) -> str:
    for key, value in scope.get("headers", []):
        if key == REQUEST_ID_HEADER:
            candidate = value.decode("latin-1").strip()
            if candidate:
                return candidate[:MAX_REQUEST_ID_LENGTH]
    return uuid4().hex


def _route(scope: Scope) -> str:
    route = scope.get("route")
    return getattr(route, "path_format", None) or scope.get("path", "")


def _client(scope: Scope) -> str:
    client = scope.get("client")
    return client[0] if client else "-"
