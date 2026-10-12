from uuid import UUID

from sqlalchemy import RowMapping, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import USER_SESSIONS_TABLE


class SQLAlchemyUserSessionRepository(UserSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_session: UserSession) -> None:
        stmt = insert(USER_SESSIONS_TABLE).values(
            id=user_session.id,
            user_id=user_session.user_id,
            expires_at=user_session.expires_at,
            created_at=user_session.created_at,
        )
        await self._session.execute(stmt)

    async def get_by_id(self, user_session_id: UUID) -> UserSession | None:
        query = select(USER_SESSIONS_TABLE).where(
            USER_SESSIONS_TABLE.c.id == user_session_id
        )
        result = await self._session.execute(query)

        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def delete_by_id(self, user_session_id: UUID) -> None:
        stmt = delete(USER_SESSIONS_TABLE).where(
            USER_SESSIONS_TABLE.c.id == user_session_id
        )
        await self._session.execute(stmt)

    def _to_entity(self, row: RowMapping) -> UserSession:
        return UserSession(
            id=row["id"],
            user_id=row["user_id"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )

    async def delete_others_for_user(
        self, user_id: UUID, keep_session_id: UUID
    ) -> None:
        await self._session.execute(
            delete(USER_SESSIONS_TABLE).where(
                USER_SESSIONS_TABLE.c.user_id == user_id,
                USER_SESSIONS_TABLE.c.id != keep_session_id,
            )
        )

    async def delete_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(USER_SESSIONS_TABLE).where(USER_SESSIONS_TABLE.c.user_id == user_id)
        )
