from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.role import Role
from myasnaya_derevnya.modules.auth.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import ROLES_TABLE


class SQLAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, role: Role) -> None:
        stmt = insert(ROLES_TABLE).values(
            id=role.id, code=role.code, name=role.name, grants_all=role.grants_all
        )
        await self._session.execute(stmt)
