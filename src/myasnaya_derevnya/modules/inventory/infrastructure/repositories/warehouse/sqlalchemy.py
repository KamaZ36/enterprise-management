from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    WAREHOUSES_TABLE,
)


class SQLAlchemyWarehouseRepository(WarehouseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, warehouse: Warehouse) -> None:
        await self._session.execute(
            insert(WAREHOUSES_TABLE).values(
                id=warehouse.id,
                org_unit_id=warehouse.org_unit_id,
                code=warehouse.code,
                name=warehouse.name,
                type=warehouse.type.value,
                is_active=warehouse.is_active,
                created_at=warehouse.created_at,
                updated_at=warehouse.updated_at,
            )
        )

    async def save(self, warehouse: Warehouse) -> None:
        await self._session.execute(
            update(WAREHOUSES_TABLE)
            .where(WAREHOUSES_TABLE.c.id == warehouse.id)
            .values(
                name=warehouse.name,
                is_active=warehouse.is_active,
                updated_at=warehouse.updated_at,
            )
        )

    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        stmt = select(WAREHOUSES_TABLE).where(WAREHOUSES_TABLE.c.id == warehouse_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_by_code(self, code: str) -> Warehouse | None:
        stmt = select(WAREHOUSES_TABLE).where(WAREHOUSES_TABLE.c.code == code)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def list(self) -> list[Warehouse]:
        stmt = select(WAREHOUSES_TABLE).order_by(WAREHOUSES_TABLE.c.code.asc())
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_entity(row) for row in rows]

    def _to_entity(self, row: RowMapping) -> Warehouse:
        return Warehouse(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            code=row["code"],
            name=row["name"],
            type=WarehouseType(row["type"]),
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
