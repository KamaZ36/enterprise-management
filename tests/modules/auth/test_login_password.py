from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from myasnaya_derevnya.modules.auth.application.errors import (
    IncorrectCredentials,
    TooManyLoginAttempts,
)
from myasnaya_derevnya.modules.auth.application.interactors.login import (
    password as login_password,
)
from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordCommand,
    LoginByPasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.services.password_login_policy import (
    PasswordLoginPolicy,
)
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.application.services.session_token import (
    hash_session_token,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.entities.login_attempt import LoginAttempt
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession

USERNAME = "ivan"
PASSWORD = "secret-password"


class FakeUserIdentityRepository:
    def __init__(self, identity: UserIdentity | None) -> None:
        self.identity = identity

    async def get_by_identifier_and_type(
        self, identifier: str, identity_type: UserIdentityType
    ) -> UserIdentity | None:
        if (
            self.identity is None
            or self.identity.identifier != identifier
            or self.identity.identity_type != identity_type
        ):
            return None

        return self.identity


class FakeCredentialRepository:
    def __init__(self, credential: UserCredential | None) -> None:
        self.credential = credential

    async def get_by_user_id_and_type(
        self, user_id: UUID, credential_type: UserCredentialType
    ) -> UserCredential | None:
        if (
            self.credential is None
            or self.credential.user_id != user_id
            or self.credential.credential_type != credential_type
        ):
            return None

        return self.credential


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        if self.user is None or self.user.id != user_id:
            return None

        return self.user


class FakeUserSessionRepository:
    def __init__(self) -> None:
        self.added: list[UserSession] = []

    async def add(self, session: UserSession) -> None:
        self.added.append(session)


class FakeLoginAttemptRepository:
    def __init__(self) -> None:
        self.attempts: dict[str, LoginAttempt] = {}
        self.stale_calls: list[datetime] = []

    async def get_by_identifier(self, identifier: str) -> LoginAttempt | None:
        return self.attempts.get(identifier)

    async def save(self, attempt: LoginAttempt) -> None:
        self.attempts[attempt.identifier] = attempt

    async def delete_by_identifier(self, identifier: str) -> None:
        self.attempts.pop(identifier, None)

    async def delete_stale(self, older_than: datetime) -> int:
        self.stale_calls.append(older_than)
        return 0


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


MAX_ATTEMPTS = 3


class Harness:
    def __init__(self, user: User | None) -> None:
        password_service = PasswordService()
        self.user = user
        self.user_id = user.id if user is not None else None
        self.identity = UserIdentity.create(
            user_id=self.user_id,
            identity_type=UserIdentityType.USERNAME,
            identifier=USERNAME,
        )
        self.credential = UserCredential.create(
            user_id=self.user_id,
            credential_type=UserCredentialType.PASSWORD,
            secret=password_service.hash(PASSWORD),
        )
        self.attempts = FakeLoginAttemptRepository()
        self.sessions = FakeUserSessionRepository()
        self.transactions = FakeTransactionManager()
        self.interactor = LoginByPasswordInteractor(
            identity_repository=FakeUserIdentityRepository(self.identity),
            credential_repository=FakeCredentialRepository(self.credential),
            user_repository=FakeUserRepository(user),
            login_attempt_repository=self.attempts,
            session_repository=self.sessions,
            transaction_manager=self.transactions,
            password_service=password_service,
            password_login_policy=PasswordLoginPolicy(
                max_attempts=MAX_ATTEMPTS,
                window=timedelta(minutes=15),
                lockout=timedelta(minutes=15),
            ),
        )


def build(user: User | None = None) -> Harness:
    if user is None:
        user = User.create()

    return Harness(user)


async def test_active_user_gets_session() -> None:
    harness = build()

    token = await harness.interactor(
        LoginByPasswordCommand(username=USERNAME, password=PASSWORD)
    )

    session = harness.sessions.added[0]
    assert isinstance(token, str)
    assert token != str(session.id)
    assert session.token_hash == hash_session_token(token)
    assert session.user_id == harness.user_id
    assert len(harness.sessions.added) == 1
    assert harness.transactions.commits == 1


async def test_blocked_user_cannot_log_in() -> None:
    user = User.create()
    user.block()
    harness = build(user)

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password=PASSWORD)
        )

    assert harness.sessions.added == []
    assert harness.transactions.commits == 1


async def test_wrong_password_does_not_create_session() -> None:
    harness = build()

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password="wrong-password")
        )

    assert harness.sessions.added == []


async def test_failures_lock_login_even_with_correct_password() -> None:
    harness = build()

    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(IncorrectCredentials):
            await harness.interactor(
                LoginByPasswordCommand(username=USERNAME, password="wrong-password")
            )

    assert harness.attempts.attempts[USERNAME].failed_attempts == MAX_ATTEMPTS

    with pytest.raises(TooManyLoginAttempts) as exc_info:
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password=PASSWORD)
        )

    assert exc_info.value.retry_after_seconds > 0
    assert harness.sessions.added == []


async def test_success_clears_failure_counter() -> None:
    harness = build()

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password="wrong-password")
        )
    await harness.interactor(
        LoginByPasswordCommand(username=USERNAME, password=PASSWORD)
    )

    assert harness.attempts.attempts == {}
    assert len(harness.sessions.added) == 1


async def test_unknown_user_is_throttled_too() -> None:
    harness = build()

    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(IncorrectCredentials):
            await harness.interactor(
                LoginByPasswordCommand(username="unknown", password="whatever")
            )

    with pytest.raises(TooManyLoginAttempts):
        await harness.interactor(
            LoginByPasswordCommand(username="unknown", password="whatever")
        )

    assert harness.sessions.added == []


async def test_failures_reset_after_window(monkeypatch) -> None:
    harness = build()
    clock = [datetime(2026, 1, 1, 12, 0, tzinfo=UTC)]
    monkeypatch.setattr(login_password, "get_datetime_utc", lambda: clock[0])

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password="wrong-password")
        )
    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password="wrong-password")
        )

    clock[0] = clock[0] + timedelta(minutes=16)

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password="wrong-password")
        )

    attempt = harness.attempts.attempts[USERNAME]
    assert attempt.failed_attempts == 1
    assert attempt.is_locked(clock[0]) is False


async def test_username_is_normalized_for_throttling() -> None:
    harness = build()

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=" IVAN ", password="wrong-password")
        )

    assert USERNAME in harness.attempts.attempts
