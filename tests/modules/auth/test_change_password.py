from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.modules.auth.application.errors import IncorrectCredentials
from myasnaya_derevnya.modules.auth.application.interactors.change_password import (
    ChangePasswordCommand,
    ChangePasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)

CURRENT = "old-password-123"
NEW = "new-password-456"


class FakeIdentityProvider:
    def __init__(self, user_id: UUID, session_id: UUID) -> None:
        self._user_id = user_id
        self._session_id = session_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id

    async def get_current_session_id(self) -> UUID:
        return self._session_id


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
        self.deleted: list[tuple[UUID, UUID]] = []

    async def delete_others_for_user(
        self, user_id: UUID, keep_session_id: UUID
    ) -> None:
        self.deleted.append((user_id, keep_session_id))


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def build(
    *,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    credential: UserCredential | None = None,
):
    password_service = PasswordService()
    user_id = user_id or uuid4()
    session_id = session_id or uuid4()

    if credential is None:
        credential = UserCredential.create(
            user_id=user_id,
            credential_type=UserCredentialType.PASSWORD,
            secret=password_service.hash(CURRENT),
        )

    credentials = FakeCredentialRepository(credential)
    sessions = FakeUserSessionRepository()
    transaction_manager = FakeTransactionManager()
    interactor = ChangePasswordInteractor(
        identity_provider=FakeIdentityProvider(user_id, session_id),
        credential_repository=credentials,
        user_session_repository=sessions,
        password_service=password_service,
        transaction_manager=transaction_manager,
    )

    return interactor, credentials, sessions, transaction_manager, user_id, session_id


async def test_wrong_current_password_is_rejected() -> None:
    interactor, credentials, sessions, transaction_manager, _, _ = build()

    with pytest.raises(IncorrectCredentials):
        await interactor(
            ChangePasswordCommand(current_password="не тот", new_password=NEW)
        )

    assert credentials.saved == []
    assert sessions.deleted == []
    assert transaction_manager.commits == 0


async def test_missing_password_credential_is_rejected() -> None:
    password_service = PasswordService()
    credential = UserCredential.create(
        user_id=uuid4(),
        credential_type=UserCredentialType.PASSWORD,
        secret=password_service.hash(CURRENT),
    )
    interactor, _, _, _, _, _ = build(credential=credential)

    with pytest.raises(IncorrectCredentials):
        await interactor(
            ChangePasswordCommand(current_password=CURRENT, new_password=NEW)
        )


async def test_password_is_changed_and_other_sessions_closed() -> None:
    interactor, credentials, sessions, transaction_manager, user_id, session_id = (
        build()
    )

    await interactor(ChangePasswordCommand(current_password=CURRENT, new_password=NEW))

    assert len(credentials.saved) == 1
    password_service = PasswordService()
    assert password_service.verify(NEW, credentials.saved[0].secret)
    assert not password_service.verify(CURRENT, credentials.saved[0].secret)
    assert sessions.deleted == [(user_id, session_id)]
    assert transaction_manager.commits == 1
