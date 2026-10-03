from uuid import UUID

from sqlalchemy import RowMapping, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.user_role import UserRole
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_role.base import (
    UserRoleRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import USER_ROLES_TABLE


class SQLAlchemyUserRoleRepository(UserRoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_role: UserRole) -> None:
        stmt = insert(USER_ROLES_TABLE).values(
            id=user_role.id,
            user_id=user_role.user_id,
            role_id=user_role.role_id,
            location_id=user_role.location_id,
            created_at=user_role.created_at,
            created_by=user_role.created_by,
        )
        await self._session.execute(stmt)

    async def get_by_user_id(self, user_id: UUID) -> UserRole | None:
        stmt = select(USER_ROLES_TABLE).where(USER_ROLES_TABLE.c.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            raise NotImplementedError

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> UserRole:
        return UserRole(
            id=row["id"],
            user_id=row["user_id"],
            role_id=row["role_id"],
            location_id=row["location_id"],
            created_at=row["created_at"],
            created_by=row["created_by"],
        )
