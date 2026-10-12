from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.dto import WarehouseListItem
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import WarehouseType
from myasnaya_derevnya.modules.inventory.infrastructure.readers.warehouse.base import (
    WarehouseReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import WAREHOUSES_TABLE


class SQLAlchemyWarehouseReader(WarehouseReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[WarehouseListItem]:
        stmt = select(WAREHOUSES_TABLE).order_by(WAREHOUSES_TABLE.c.name.asc())
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows]

    @staticmethod
    def _to_dto(row: RowMapping) -> WarehouseListItem:
        return WarehouseListItem(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            code=row["code"],
            name=row["name"],
            type=WarehouseType(row["type"]),
            is_active=row["is_active"],
        )
