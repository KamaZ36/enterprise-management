from sqlalchemy import RowMapping, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.application.dto import RoleListItem
from myasnaya_derevnya.modules.staff.infrastructure.readers.role.base import RoleReader
from myasnaya_derevnya.modules.staff.infrastructure.tables import (
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
)


class SQLAlchemyRoleReader(RoleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[RoleListItem]:
        permission_codes = func.array_agg(
            ROLE_PERMISSIONS_TABLE.c.permission_code
        ).filter(ROLE_PERMISSIONS_TABLE.c.permission_code.is_not(None))

        stmt = (
            select(
                ROLES_TABLE.c.id,
                ROLES_TABLE.c.code,
                ROLES_TABLE.c.name,
                ROLES_TABLE.c.description,
                ROLES_TABLE.c.level,
                ROLES_TABLE.c.is_system,
                ROLES_TABLE.c.is_assignable,
                ROLES_TABLE.c.is_wildcard,
                permission_codes.label("permission_codes"),
            )
            .select_from(
                ROLES_TABLE.outerjoin(
                    ROLE_PERMISSIONS_TABLE,
                    ROLE_PERMISSIONS_TABLE.c.role_id == ROLES_TABLE.c.id,
                )
            )
            .group_by(
                ROLES_TABLE.c.id,
                ROLES_TABLE.c.code,
                ROLES_TABLE.c.name,
                ROLES_TABLE.c.description,
                ROLES_TABLE.c.level,
                ROLES_TABLE.c.is_system,
                ROLES_TABLE.c.is_assignable,
                ROLES_TABLE.c.is_wildcard,
            )
            .order_by(ROLES_TABLE.c.level.desc(), ROLES_TABLE.c.name.asc())
        )

        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows]

    def _to_dto(self, row: RowMapping) -> RoleListItem:
        return RoleListItem(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            description=row["description"],
            level=row["level"],
            is_system=row["is_system"],
            is_assignable=row["is_assignable"],
            is_wildcard=row["is_wildcard"],
            permission_codes=frozenset(row["permission_codes"] or ()),
        )
