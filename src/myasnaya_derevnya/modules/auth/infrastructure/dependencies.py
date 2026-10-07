from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.create_employee_credential import (
    CreateEmployeeCredentialInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.create_user import (
    CreateUserInteractor,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.sqlalchemy import (
    SQLAlchemyCredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.sqlalchemy import (
    SQLAlchemyUserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.sqlalchemy import (
    SQLAlchemyUserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.sqlalchemy import (
    SQLAlchemyUserSessionRepository,
)
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService


class AuthDepProvider(Provider):
    # REPOSITORIES
    @provide(scope=Scope.REQUEST)
    def get_credential_repository(self, session: AsyncSession) -> CredentialRepository:
        return SQLAlchemyCredentialRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return SQLAlchemyUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_session_repository(
        self, session: AsyncSession
    ) -> UserSessionRepository:
        return SQLAlchemyUserSessionRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_identity_repository(
        self, session: AsyncSession
    ) -> UserIdentityRepository:
        return SQLAlchemyUserIdentityRepository(session)

    # SERVICES

    password_service = provide(PasswordService, scope=Scope.REQUEST)

    # INTERACTORS

    login_by_password_interactor = provide(
        LoginByPasswordInteractor, scope=Scope.REQUEST
    )

    create_user_interactor = provide(CreateUserInteractor, scope=Scope.REQUEST)
    create_employee_credential = provide(
        CreateEmployeeCredentialInteractor, scope=Scope.REQUEST
    )

    # FACADE
    auth_api = provide(AuthAPI, scope=Scope.REQUEST)
