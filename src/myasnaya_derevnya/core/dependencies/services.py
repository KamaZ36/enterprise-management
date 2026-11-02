from dishka import Provider, Scope, from_context, provide
from fastapi import Request

from myasnaya_derevnya.core.identity_provider import (
    IdentityProvider,
    SessionTokenGetter,
)
from myasnaya_derevnya.core.media.paths import media_root
from myasnaya_derevnya.core.media.storage import LocalDiskStorage, MediaStorage
from myasnaya_derevnya.core.settings.media import MediaSettings
from myasnaya_derevnya.core.settings.ofd import OfdSettings
from myasnaya_derevnya.modules.auth.infrastructure.identity_provider import (
    HTTPBearerTokenGetter,
    HTTPIdentityProvider,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
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
    def get_ofd_settings(self) -> OfdSettings:
        return OfdSettings()

    @provide(scope=Scope.APP)
    def get_media_storage(self, media_settings: MediaSettings) -> MediaStorage:
        return LocalDiskStorage(
            root=media_root(media_settings),
            url_prefix=media_settings.media_url_prefix,
        )

    @provide(scope=Scope.REQUEST)
    def get_session_token_getter(self, request: Request) -> SessionTokenGetter:
        return HTTPBearerTokenGetter(request)

    @provide(scope=Scope.REQUEST)
    def get_identity_provider(
        self,
        session_token_getter: SessionTokenGetter,
        session_repository: UserSessionRepository,
        user_repository: UserRepository,
    ) -> IdentityProvider:
        return HTTPIdentityProvider(
            session_token_getter=session_token_getter,
            session_repository=session_repository,
            user_repository=user_repository,
        )
