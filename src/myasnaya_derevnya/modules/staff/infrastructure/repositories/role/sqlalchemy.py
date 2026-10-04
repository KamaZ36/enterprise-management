from uuid import UUID

from sqlalchemy import RowMapping, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.tables import (
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
)


class SQLAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, role: Role) -> None:
        await self._session.execute(
            insert(ROLES_TABLE).values(
                id=role.id,
                code=role.code,
                name=role.name,
                grants_all=role.grants_all,
            )
        )

        if role.permissions:
            await self._session.execute(
                insert(ROLE_PERMISSIONS_TABLE).values(
                    [
                        {
                            "role_id": role.id,
                            "permission_code": permission_code,
                        }
                        for permission_code in role.permissions
                    ]
                )
            )

    async def get_by_id(self, role_id: UUID) -> Role | None:
        stmt = (
            select(
                ROLES_TABLE.c.id,
                ROLES_TABLE.c.code,
                ROLES_TABLE.c.name,
                ROLES_TABLE.c.grants_all,
                func.array_agg(ROLE_PERMISSIONS_TABLE.c.permission_code)
                .filter(ROLE_PERMISSIONS_TABLE.c.permission_code.is_not(None))
                .label("permission_codes"),
            )
            .select_from(
                ROLES_TABLE.outerjoin(
                    ROLE_PERMISSIONS_TABLE,
                    ROLE_PERMISSIONS_TABLE.c.role_id == ROLES_TABLE.c.id,
                )
            )
            .where(ROLES_TABLE.c.id == role_id)
            .group_by(ROLES_TABLE.c.id)
        )

        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> Role:
        return Role(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            grants_all=row["grants_all"],
            permissions=frozenset(row["permission_codes"] or ()),
        )
