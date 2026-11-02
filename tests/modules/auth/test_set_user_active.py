from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.modules.auth.application.errors import UserNotFound
from myasnaya_derevnya.modules.auth.application.interactors.system.set_user_active import (
    SetUserActiveCommand,
    SetUserActiveInteractor,
)
from myasnaya_derevnya.modules.auth.domain.entities.user import User, UserStatus


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.saved: list[User] = []

    async def get_by_id(self, user_id: UUID) -> User | None:
        if self.user is None or self.user.id != user_id:
            return None

        return self.user

    async def save(self, user: User) -> None:
        self.saved.append(user)


class FakeUserSessionRepository:
    def __init__(self) -> None:
        self.deleted_for: list[UUID] = []

    async def delete_all_for_user(self, user_id: UUID) -> None:
        self.deleted_for.append(user_id)


def build(user: User | None = None):
    if user is None:
        user = User.create()

    users = FakeUserRepository(user)
    sessions = FakeUserSessionRepository()
    interactor = SetUserActiveInteractor(
        user_repository=users,
        session_repository=sessions,
    )

    return interactor, users, sessions, user


async def test_block_sets_status_and_deletes_sessions() -> None:
    interactor, users, sessions, user = build()

    await interactor(SetUserActiveCommand(user_id=user.id, is_active=False))

    assert user.status is UserStatus.BLOCKED
    assert user.is_active is False
    assert sessions.deleted_for == [user.id]
    assert users.saved == [user]


async def test_unblock_restores_status_without_touching_sessions() -> None:
    user = User.create()
    user.block()
    interactor, users, sessions, _ = build(user)

    await interactor(SetUserActiveCommand(user_id=user.id, is_active=True))

    assert user.status is UserStatus.ACTIVE
    assert user.is_active is True
    assert sessions.deleted_for == []
    assert users.saved == [user]


async def test_unknown_user_raises_not_found() -> None:
    interactor, users, sessions, _ = build()

    with pytest.raises(UserNotFound):
        await interactor(SetUserActiveCommand(user_id=uuid4(), is_active=False))

    assert users.saved == []
    assert sessions.deleted_for == []
