from datetime import timedelta

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.auth.application.interactors.change_password import (
    ChangePasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.logout import (
    LogoutInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.create_employee_credential import (
    CreateEmployeeCredentialInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.create_user import (
    CreateUserInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.ensure_user_by_phone import (
    EnsureUserByPhoneInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.request_login_code import (
    RequestLoginCodeInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.reset_employee_password import (
    ResetEmployeePasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.start_session import (
    StartSessionInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.verify_login_code import (
    VerifyLoginCodeInteractor,
)
from myasnaya_derevnya.modules.auth.application.services.login_code_service import (
    LoginCodeService,
)
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
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
from myasnaya_derevnya.modules.auth.infrastructure.repositories.one_time_code.base import (
    OneTimeCodeRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.one_time_code.sqlalchemy import (
    SQLAlchemyOneTimeCodeRepository,
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
from myasnaya_derevnya.modules.auth.infrastructure.service.login_code_sender.base import (
    LoginCodeSender,
)
from myasnaya_derevnya.modules.auth.infrastructure.service.login_code_sender.cli import (
    LoggingLoginCodeSender,
)
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI


class AuthDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_one_time_code_repository(
        self, session: AsyncSession
    ) -> OneTimeCodeRepository:
        return SQLAlchemyOneTimeCodeRepository(session)

    @provide(scope=Scope.APP)
    def get_login_code_service(self) -> LoginCodeService:
        return LoginCodeService(
            secret=settings.login_code_secret,
            code_length=settings.login_code_length,
            ttl=timedelta(seconds=settings.login_code_ttl_seconds),
            max_attempts=settings.login_code_max_attempts,
            min_interval=timedelta(seconds=settings.login_code_min_interval_seconds),
            hourly_limit=settings.login_code_hourly_limit,
        )

    @provide(scope=Scope.APP)
    def get_login_code_sender(self) -> LoginCodeSender:
        return LoggingLoginCodeSender()


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


    password_service = provide(PasswordService, scope=Scope.REQUEST)


    logout_interactor = provide(LogoutInteractor, scope=Scope.REQUEST)

    change_password_interactor = provide(ChangePasswordInteractor, scope=Scope.REQUEST)

    reset_employee_password_interactor = provide(
        ResetEmployeePasswordInteractor, scope=Scope.REQUEST
    )

    login_by_password_interactor = provide(
        LoginByPasswordInteractor, scope=Scope.REQUEST
    )

    create_user_interactor = provide(CreateUserInteractor, scope=Scope.REQUEST)
    create_employee_credential = provide(
        CreateEmployeeCredentialInteractor, scope=Scope.REQUEST
    )

    ensure_user_by_phone_interactor = provide(
        EnsureUserByPhoneInteractor, scope=Scope.REQUEST
    )

    request_login_code_interactor = provide(
        RequestLoginCodeInteractor, scope=Scope.REQUEST
    )

    verify_login_code_interactor = provide(
        VerifyLoginCodeInteractor, scope=Scope.REQUEST
    )

    start_session_interactor = provide(StartSessionInteractor, scope=Scope.REQUEST)


    auth_api = provide(AuthAPI, scope=Scope.REQUEST)
