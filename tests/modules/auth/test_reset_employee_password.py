from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.modules.auth.application.errors import UserNotFound
from myasnaya_derevnya.modules.auth.application.interactors.system.reset_employee_password import (
    ResetEmployeePasswordCommand,
    ResetEmployeePasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)

OLD = "old-password-123"
NEW = "brand-new-456"


class FakeCredentialRepository:
    def __init__(self, credential: UserCredential | None) -> None:
        self.credential = credential
        self.saved: list[UserCredential] = []

    async def get_by_user_id_and_type(self, user_id: UUID, credential_type):
        if self.credential is None:
            return None

        return (
            self.credential
            if self.credential.user_id == user_id
            and self.credential.credential_type == credential_type
            else None
        )

    async def save(self, credential: UserCredential) -> None:
        self.saved.append(credential)


class FakeUserSessionRepository:
    def __init__(self) -> None:
        self.closed: list[UUID] = []

    async def delete_all_for_user(self, user_id: UUID) -> None:
        self.closed.append(user_id)


class Harness:
    def __init__(self, credential: UserCredential | None) -> None:
        self.password_service = PasswordService()
        self.credentials = FakeCredentialRepository(credential)
        self.sessions = FakeUserSessionRepository()
        self.credential = credential
        self.interactor = ResetEmployeePasswordInteractor(
            credential_repository=self.credentials,
            user_session_repository=self.sessions,
            password_service=self.password_service,
        )


def build(credential: UserCredential | None = None) -> Harness:
    if credential is None:
        credential = UserCredential.create(
            user_id=uuid4(),
            credential_type=UserCredentialType.PASSWORD,
            secret=PasswordService().hash(OLD),
        )

    return Harness(credential)


async def test_password_is_replaced_and_sessions_closed() -> None:
    harness = build()
    assert harness.credential is not None

    await harness.interactor(
        ResetEmployeePasswordCommand(user_id=harness.credential.user_id, password=NEW)
    )

    assert len(harness.credentials.saved) == 1
    assert harness.password_service.verify(NEW, harness.credentials.saved[0].secret)
    assert not harness.password_service.verify(OLD, harness.credentials.saved[0].secret)
    assert harness.sessions.closed == [harness.credential.user_id]


async def test_missing_credential_raises_user_not_found() -> None:
    harness = build(
        UserCredential.create(
            user_id=uuid4(),
            credential_type=UserCredentialType.PASSWORD,
            secret="hash",
        )
    )

    with pytest.raises(UserNotFound):
        await harness.interactor(
            ResetEmployeePasswordCommand(user_id=uuid4(), password=NEW)
        )

    assert harness.credentials.saved == []
    assert harness.sessions.closed == []
