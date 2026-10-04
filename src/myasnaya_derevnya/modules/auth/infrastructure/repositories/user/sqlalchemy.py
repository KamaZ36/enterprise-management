from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.user import User, UserStatus
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import USERS_TABLE


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        stmt = insert(USERS_TABLE).values(
            id=user.id, status=user.status.value, created_at=user.created_at
        )
        await self._session.execute(stmt)

    async def save(self, user: User) -> None:
        stmt = (
            update(USERS_TABLE)
            .where(USERS_TABLE.c.id == user.id)
            .values(status=user.status.value)
        )
        await self._session.execute(stmt)

    async def get_by_id(self, user_id: UUID) -> User | None:
        query = select(USERS_TABLE).where(USERS_TABLE.c.id == user_id)
        result = await self._session.execute(query)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> User:
        return User(
            id=row["id"], status=UserStatus(row["status"]), created_at=row["created_at"]
        )
