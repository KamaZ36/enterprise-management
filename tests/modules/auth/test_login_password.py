from uuid import UUID

import pytest

from myasnaya_derevnya.modules.auth.application.errors import IncorrectCredentials
from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordCommand,
    LoginByPasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
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


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


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
        self.sessions = FakeUserSessionRepository()
        self.transactions = FakeTransactionManager()
        self.interactor = LoginByPasswordInteractor(
            identity_repository=FakeUserIdentityRepository(self.identity),
            credential_repository=FakeCredentialRepository(self.credential),
            user_repository=FakeUserRepository(user),
            session_repository=self.sessions,
            transaction_manager=self.transactions,
            password_service=password_service,
        )


def build(user: User | None = None) -> Harness:
    if user is None:
        user = User.create()

    return Harness(user)


async def test_active_user_gets_session() -> None:
    harness = build()

    session_id = await harness.interactor(
        LoginByPasswordCommand(username=USERNAME, password=PASSWORD)
    )

    assert session_id == harness.sessions.added[0].id
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
    assert harness.transactions.commits == 0


async def test_wrong_password_does_not_create_session() -> None:
    harness = build()

    with pytest.raises(IncorrectCredentials):
        await harness.interactor(
            LoginByPasswordCommand(username=USERNAME, password="wrong-password")
        )

    assert harness.sessions.added == []
