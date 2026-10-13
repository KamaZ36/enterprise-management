from datetime import timedelta
from uuid import UUID

from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc


class StartSessionInteractor:
    def __init__(self, session_repository: UserSessionRepository) -> None:
        self._session_repository = session_repository

    async def __call__(self, user_id: UUID) -> UUID:
        session = UserSession.create(
            user_id=user_id,
            expires_at=get_datetime_utc() + timedelta(days=30),
        )
        await self._session_repository.add(session)

        return session.id
