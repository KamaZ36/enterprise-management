from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.application.dto import RoleListItem
from myasnaya_derevnya.modules.staff.infrastructure.readers.role.base import RoleReader
from myasnaya_derevnya.modules.staff.infrastructure.tables import ROLES_TABLE


class SQLAlchemyRoleReader(RoleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[RoleListItem]:
        stmt = select(
            ROLES_TABLE.c.id,
            ROLES_TABLE.c.code,
            ROLES_TABLE.c.name,
            ROLES_TABLE.c.level,
            ROLES_TABLE.c.is_system,
            ROLES_TABLE.c.is_assignable,
            ROLES_TABLE.c.is_wildcard,
        ).order_by(ROLES_TABLE.c.level.desc(), ROLES_TABLE.c.name.asc())

        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows]

    def _to_dto(self, row: RowMapping) -> RoleListItem:
        return RoleListItem(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            level=row["level"],
            is_system=row["is_system"],
            is_assignable=row["is_assignable"],
            is_wildcard=row["is_wildcard"],
        )
