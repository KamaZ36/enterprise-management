from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import UnauthorizedError
from myasnaya_derevnya.modules.auth.application.services.session_token import (
    generate_session_token,
    hash_session_token,
)
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.identity_provider import (
    HTTPIdentityProvider,
)
from myasnaya_derevnya.utils import get_datetime_utc


class FakeSessionTokenGetter:
    def __init__(self, token: str | None) -> None:
        self.token = token

    async def get(self) -> str | None:
        return self.token


class FakeSessionRepository:
    def __init__(self, session: UserSession | None) -> None:
        self.session = session

    async def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        if self.session is None or self.session.token_hash != token_hash:
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
    token = generate_session_token()
    session = UserSession.create(
        user_id=user_id,
        token_hash=hash_session_token(token),
        expires_at=get_datetime_utc() + expires_in,
    )
    provider = HTTPIdentityProvider(
        session_token_getter=FakeSessionTokenGetter(token),
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


async def test_unknown_token_is_rejected() -> None:
    user = User.create()
    session = UserSession.create(
        user_id=user.id,
        token_hash=hash_session_token(generate_session_token()),
        expires_at=get_datetime_utc() + timedelta(days=1),
    )
    provider = HTTPIdentityProvider(
        session_token_getter=FakeSessionTokenGetter(generate_session_token()),
        session_repository=FakeSessionRepository(session),
        user_repository=FakeUserRepository(user),
    )

    with pytest.raises(UnauthorizedError):
        await provider.get_current_user_id()


async def test_unknown_user_is_rejected() -> None:
    token = generate_session_token()
    session = UserSession.create(
        user_id=uuid4(),
        token_hash=hash_session_token(token),
        expires_at=get_datetime_utc() + timedelta(days=1),
    )
    provider = HTTPIdentityProvider(
        session_token_getter=FakeSessionTokenGetter(token),
        session_repository=FakeSessionRepository(session),
        user_repository=FakeUserRepository(None),
    )

    with pytest.raises(UnauthorizedError):
        await provider.get_current_user_id()
