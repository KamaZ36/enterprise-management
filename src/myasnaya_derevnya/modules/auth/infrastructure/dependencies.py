from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordInteractor,
)
from myasnaya_derevnya.modules.auth.infrastructure.readers.access_reader.base import (
    AccessReader,
)
from myasnaya_derevnya.modules.auth.infrastructure.readers.access_reader.sqlalchemy import (
    SQLAlchemyAccessReader,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.sqlalchemy import (
    SQLAlchemyCredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.role.sqlalchemy import (
    SQLAlchemyRoleRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.sqlalchemy import (
    SQLAlchemyUserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_role.base import (
    UserRoleRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_role.sqlalchemy import (
    SQLAlchemyUserRoleRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.sqlalchemy import (
    SQLAlchemyUserSessionRepository,
)
from myasnaya_derevnya.modules.auth.presentation.facade import AuthFacade
from myasnaya_derevnya.modules.auth.services.access_service import AccessService
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService


class AuthDepProvider(Provider):
    # REPOSITORIES
    @provide(scope=Scope.REQUEST)
    def get_credential_repository(self, session: AsyncSession) -> CredentialRepository:
        return SQLAlchemyCredentialRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_role_repository(self, session: AsyncSession) -> RoleRepository:
        return SQLAlchemyRoleRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return SQLAlchemyUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_role_repository(self, session: AsyncSession) -> UserRoleRepository:
        return SQLAlchemyUserRoleRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_session_repository(
        self, session: AsyncSession
    ) -> UserSessionRepository:
        return SQLAlchemyUserSessionRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_access_reader(self, session: AsyncSession) -> AccessReader:
        return SQLAlchemyAccessReader(session)

    # SERVICES

    password_service = provide(PasswordService, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def get_access_serivce(self, access_reader: AccessReader) -> AccessService:
        return AccessService(access_reader)

    # INTERACTORS

    login_by_password_interactor = provide(
        LoginByPasswordInteractor, scope=Scope.REQUEST
    )

    # FACADE
    auth_facade = provide(AuthFacade, scope=Scope.REQUEST)
