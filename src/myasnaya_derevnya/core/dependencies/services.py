from dishka import Provider, Scope, from_context, provide
from fastapi import Request

from myasnaya_derevnya.core.identity_provider import IdentityProvider, SessionIdGetter
from myasnaya_derevnya.modules.auth.infrastructure.identity_provider import (
    HTTPIdentityProvider,
    HTTPSessionIDGetter,
)
from myasnaya_derevnya.modules.auth.infrastructure.readers.access_reader.base import (
    AccessReader,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.services.access_service import AccessService
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService


class ServicesDepProvider(Provider):
    request = from_context(provides=Request, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def get_session_id_getter(self, request: Request) -> SessionIdGetter:
        return HTTPSessionIDGetter(request)

    @provide(scope=Scope.REQUEST)
    def get_identity_provider(
        self,
        session_id_getter: SessionIdGetter,
        session_repository: UserSessionRepository,
    ) -> IdentityProvider:
        return HTTPIdentityProvider(
            session_id_getter=session_id_getter, session_repository=session_repository
        )

    # MODULE AUTH

    password_service = provide(PasswordService, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def get_access_serivce(self, access_reader: AccessReader) -> AccessService:
        return AccessService(access_reader)
