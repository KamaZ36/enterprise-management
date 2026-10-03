from uuid import UUID

from fastapi import Request

from myasnaya_derevnya.core.errors import UnauthorizedError
from myasnaya_derevnya.core.identity_provider import IdentityProvider, SessionIdGetter
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc


class HTTPSessionIDGetter(SessionIdGetter):
    def __init__(self, request: Request) -> None:
        self._request = request

    async def get(self) -> UUID | None:
        authorization = self._request.headers.get("Authorization")

        if authorization is None:
            return None

        scheme, _, value = authorization.partition(" ")

        if scheme.lower() != "bearer" or not value:
            return None

        try:
            return UUID(value)
        except ValueError:
            return None


class HTTPIdentityProvider(IdentityProvider):
    def __init__(
        self,
        session_id_getter: SessionIdGetter,
        session_repository: UserSessionRepository,
    ) -> None:
        self._session_id_getter = session_id_getter
        self._session_repository = session_repository
        self._active_session: UserSession | None = None

    async def _get_active_session(self) -> UserSession:
        if self._active_session is not None:
            return self._active_session

        session_id = await self._session_id_getter.get()

        if session_id is None:
            raise UnauthorizedError()

        session = await self._session_repository.get_by_id(session_id)

        if session is None:
            raise UnauthorizedError()

        if get_datetime_utc() > session.expires_at:
            raise UnauthorizedError()

        self._active_session = session

        return session

    async def get_current_user_id(self) -> UUID:
        session = await self._get_active_session()
        return session.user_id

    async def get_current_session_id(self) -> UUID:
        session = await self._get_active_session()
        return session.id
