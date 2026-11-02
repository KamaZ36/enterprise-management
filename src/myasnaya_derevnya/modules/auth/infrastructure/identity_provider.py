from uuid import UUID

from fastapi import Request

from myasnaya_derevnya.core.errors import UnauthorizedError
from myasnaya_derevnya.core.identity_provider import (
    IdentityProvider,
    SessionTokenGetter,
)
from myasnaya_derevnya.core.logging.context import set_user_id
from myasnaya_derevnya.modules.auth.application.services.session_token import (
    TOKEN_MAX_LENGTH,
    hash_session_token,
)
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc


class HTTPBearerTokenGetter(SessionTokenGetter):
    def __init__(self, request: Request) -> None:
        self._request = request

    async def get(self) -> str | None:
        authorization = self._request.headers.get("Authorization")

        if authorization is None:
            return None

        scheme, _, value = authorization.partition(" ")

        if scheme.lower() != "bearer":
            return None

        token = value.strip()
        if not token or len(token) > TOKEN_MAX_LENGTH:
            return None

        return token


class HTTPIdentityProvider(IdentityProvider):
    def __init__(
        self,
        session_token_getter: SessionTokenGetter,
        session_repository: UserSessionRepository,
        user_repository: UserRepository,
    ) -> None:
        self._session_token_getter = session_token_getter
        self._session_repository = session_repository
        self._user_repository = user_repository
        self._active_session: UserSession | None = None

    async def _get_active_session(self) -> UserSession:
        if self._active_session is not None:
            return self._active_session

        token = await self._session_token_getter.get()

        if token is None:
            raise UnauthorizedError()

        session = await self._session_repository.get_by_token_hash(
            hash_session_token(token)
        )

        if session is None:
            raise UnauthorizedError()

        if get_datetime_utc() > session.expires_at:
            raise UnauthorizedError()

        user = await self._user_repository.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError()

        self._active_session = session
        set_user_id(session.user_id)

        return session

    async def get_current_user_id(self) -> UUID:
        session = await self._get_active_session()
        return session.user_id

    async def get_current_session_id(self) -> UUID:
        session = await self._get_active_session()
        return session.id
