from dishka import Provider, Scope, from_context, provide
from fastapi import Request

from myasnaya_derevnya.core.identity_provider import IdentityProvider, SessionIdGetter
from myasnaya_derevnya.core.media.paths import media_root
from myasnaya_derevnya.core.media.storage import LocalDiskStorage, MediaStorage
from myasnaya_derevnya.core.settings.media import MediaSettings
from myasnaya_derevnya.modules.auth.infrastructure.identity_provider import (
    HTTPIdentityProvider,
    HTTPSessionIDGetter,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)


class ServicesDepProvider(Provider):
    request = from_context(provides=Request, scope=Scope.REQUEST)

    @provide(scope=Scope.APP)
    def get_media_settings(self) -> MediaSettings:
        return MediaSettings()

    @provide(scope=Scope.APP)
    def get_media_storage(self, media_settings: MediaSettings) -> MediaStorage:
        return LocalDiskStorage(
            root=media_root(media_settings),
            url_prefix=media_settings.media_url_prefix,
        )

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
