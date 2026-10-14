from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.business.application.dto import (
    CafeOrgUnitListItem,
    OrgUnitListItem,
)
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
            ORG_UNITS_TABLE.c.address,
            ORG_UNITS_TABLE.c.phone_number,
        ).order_by(ORG_UNITS_TABLE.c.name.asc(), ORG_UNITS_TABLE.c.code.asc())

        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            OrgUnitListItem(
                id=row["id"],
                parent_id=row["parent_id"],
                type=OrgUnitType(row["type"]),
                code=row["code"],
                name=row["name"],
                is_active=row["is_active"],
                address=row["address"],
                phone_number=row["phone_number"],
            )
            for row in rows
        ]

    async def get_cafe_list(self) -> list[CafeOrgUnitListItem]:
        stmt = select(ORG_UNITS_TABLE).where(
            ORG_UNITS_TABLE.c.type == OrgUnitType.CAFE,
            ORG_UNITS_TABLE.c.is_active == True,
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            CafeOrgUnitListItem(
                id=row["id"],
                type=OrgUnitType(row["type"]),
                code=row["code"],
                name=row["name"],
                address=row["address"],
                phone_number=row["phone_number"],
            )
            for row in rows
        ]
