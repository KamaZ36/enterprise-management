from uuid import UUID

from fastapi import Request

SCOPE_HEADER = "X-Scope-Id"


class CurrentScope:
    def __init__(self, request: Request) -> None:
        self._request = request

    def org_unit_id(self) -> UUID | None:
        raw = self._request.headers.get(SCOPE_HEADER)
        if not raw:
            return None

        try:
            return UUID(raw)
        except ValueError:
            return None
