import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.application.errors import (
    IncorrectCredentials,
    TooManyLoginAttempts,
)
from myasnaya_derevnya.modules.auth.application.services.password_login_policy import (
    PasswordLoginPolicy,
)
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.application.services.session_token import (
    generate_session_token,
    hash_session_token,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import UserCredentialType
from myasnaya_derevnya.modules.auth.domain.entities.identity import UserIdentityType
from myasnaya_derevnya.modules.auth.domain.entities.login_attempt import LoginAttempt
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.login_attempt.base import (
    LoginAttemptRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)

SESSION_TTL = timedelta(days=30)


@dataclass(frozen=True, slots=True)
class LoginByPasswordCommand:
    username: str
    password: str


class LoginByPasswordInteractor:
    def __init__(
        self,
        identity_repository: UserIdentityRepository,
        credential_repository: CredentialRepository,
        user_repository: UserRepository,
        login_attempt_repository: LoginAttemptRepository,
        session_repository: UserSessionRepository,
        transaction_manager: TransactionManager,
        password_service: PasswordService,
        password_login_policy: PasswordLoginPolicy,
    ) -> None:
        self._identity_repository = identity_repository
        self._credential_repository = credential_repository
        self._user_repository = user_repository
        self._login_attempt_repository = login_attempt_repository
        self._session_repository = session_repository
        self._transaction_manager = transaction_manager
        self._password_service = password_service
        self._password_login_policy = password_login_policy

    async def __call__(self, command: LoginByPasswordCommand) -> str:
        identifier = command.username.strip().lower()
        now = get_datetime_utc()
        attempt = await self._login_attempt_repository.get_by_identifier(identifier)

        if attempt is not None and attempt.is_locked(now):
            retry_after = attempt.retry_after_seconds(now)
            logger.warning(
                "Вход отклонён: временная блокировка",
                extra={
                    "identifier": identifier,
                    "retry_after_seconds": retry_after,
                },
            )
            raise TooManyLoginAttempts(retry_after_seconds=retry_after)

        user_identity = await self._identity_repository.get_by_identifier_and_type(
            identifier=command.username, identity_type=UserIdentityType.USERNAME
        )

        if user_identity is None:
            logger.warning("Неудачный вход: неизвестный пользователь %s", identifier)
            await self._register_failure(identifier, attempt, now)
            raise IncorrectCredentials()

        user_credential = await self._credential_repository.get_by_user_id_and_type(
            user_id=user_identity.user_id, credential_type=UserCredentialType.PASSWORD
        )

        if user_credential is None:
            logger.warning(
                "Неудачный вход: у пользователя нет пароля",
                extra={"user_id": str(user_identity.user_id)},
            )
            await self._register_failure(identifier, attempt, now)
            raise IncorrectCredentials()

        if not self._password_service.verify(command.password, user_credential.secret):
            logger.warning(
                "Неудачный вход: неверный пароль",
                extra={"user_id": str(user_credential.user_id)},
            )
            await self._register_failure(identifier, attempt, now)
            raise IncorrectCredentials()

        user = await self._user_repository.get_by_id(user_credential.user_id)
        if user is None or not user.is_active:
            logger.warning(
                "Неудачный вход: пользователь заблокирован",
                extra={"user_id": str(user_credential.user_id)},
            )
            await self._register_failure(identifier, attempt, now)
            raise IncorrectCredentials()

        if attempt is not None:
            await self._login_attempt_repository.delete_by_identifier(identifier)
        await self._login_attempt_repository.delete_stale(
            now - self._password_login_policy.retention
        )

        token = generate_session_token()
        session = UserSession.create(
            user_id=user_credential.user_id,
            token_hash=hash_session_token(token),
            expires_at=now + SESSION_TTL,
        )

        await self._session_repository.add(session)
        await self._transaction_manager.commit()

        logger.info("Вход по паролю", extra={"user_id": str(session.user_id)})

        return token

    async def _register_failure(
        self,
        identifier: str,
        attempt: LoginAttempt | None,
        now: datetime,
    ) -> None:
        if attempt is None:
            attempt = LoginAttempt.create(identifier, now)

        attempt.register_failure(
            now,
            max_attempts=self._password_login_policy.max_attempts,
            window=self._password_login_policy.window,
            lockout=self._password_login_policy.lockout,
        )

        await self._login_attempt_repository.save(attempt)
        await self._login_attempt_repository.delete_stale(
            now - self._password_login_policy.retention
        )
        await self._transaction_manager.commit()
