from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import UnauthorizedError
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.identity_provider import (
    HTTPIdentityProvider,
)
from myasnaya_derevnya.utils import get_datetime_utc


class FakeSessionIdGetter:
    def __init__(self, session_id: UUID | None) -> None:
        self.session_id = session_id

    async def get(self) -> UUID | None:
        return self.session_id


class FakeSessionRepository:
    def __init__(self, session: UserSession | None) -> None:
        self.session = session

    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        if self.session is None or self.session.id != session_id:
            return None

        return self.session


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        if self.user is None or self.user.id != user_id:
            return None

        return self.user


def build(user: User | None, *, expires_in: timedelta = timedelta(days=1)):
    user_id = user.id if user is not None else uuid4()
    session = UserSession.create(
        user_id=user_id, expires_at=get_datetime_utc() + expires_in
    )
    provider = HTTPIdentityProvider(
        session_id_getter=FakeSessionIdGetter(session.id),
        session_repository=FakeSessionRepository(session),
        user_repository=FakeUserRepository(user),
    )

    return provider, user_id


async def test_active_user_is_authenticated() -> None:
    user = User.create()
    provider, user_id = build(user)

    assert await provider.get_current_user_id() == user_id


async def test_blocked_user_session_is_rejected() -> None:
    user = User.create()
    user.block()
    provider, _ = build(user)

    with pytest.raises(UnauthorizedError):
        await provider.get_current_user_id()


async def test_expired_session_is_rejected() -> None:
    user = User.create()
    provider, _ = build(user, expires_in=timedelta(seconds=-1))

    with pytest.raises(UnauthorizedError):
        await provider.get_current_user_id()


async def test_unknown_user_is_rejected() -> None:
    session = UserSession.create(
        user_id=uuid4(), expires_at=get_datetime_utc() + timedelta(days=1)
    )
    provider = HTTPIdentityProvider(
        session_id_getter=FakeSessionIdGetter(session.id),
        session_repository=FakeSessionRepository(session),
        user_repository=FakeUserRepository(None),
    )

    with pytest.raises(UnauthorizedError):
        await provider.get_current_user_id()
