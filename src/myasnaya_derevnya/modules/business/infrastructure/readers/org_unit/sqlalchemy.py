from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem
from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType
from myasnaya_derevnya.modules.business.infrastructure.readers.org_unit.base import (
    OrgUnitReader,
)
from myasnaya_derevnya.modules.business.infrastructure.tables import ORG_UNITS_TABLE


class SQLAlchemyOrgUnitReader(OrgUnitReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[OrgUnitListItem]:
        stmt = select(
            ORG_UNITS_TABLE.c.id,
            ORG_UNITS_TABLE.c.parent_id,
            ORG_UNITS_TABLE.c.type,
            ORG_UNITS_TABLE.c.code,
            ORG_UNITS_TABLE.c.name,
            ORG_UNITS_TABLE.c.is_active,
        ).order_by(ORG_UNITS_TABLE.c.name.asc(), ORG_UNITS_TABLE.c.code.asc())

        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows]

    def _to_dto(self, row: RowMapping) -> OrgUnitListItem:
        return OrgUnitListItem(
            id=row["id"],
            parent_id=row["parent_id"],
            type=OrgUnitType(row["type"]),
            code=row["code"],
            name=row["name"],
            is_active=row["is_active"],
        )
