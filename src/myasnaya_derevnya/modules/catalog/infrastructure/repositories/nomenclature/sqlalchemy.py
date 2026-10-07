from uuid import UUID

from sqlalchemy import RowMapping, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import NOMENCLATURES_TABLE


class SQLAlchemyNomenclatureRepository(NomenclatureRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, nomenclature: Nomenclature) -> None:
        await self._session.execute(
            insert(NOMENCLATURES_TABLE).values(
                id=nomenclature.id,
                sku=nomenclature.sku,
                name=nomenclature.name,
                unit=nomenclature.unit.value,
                type=nomenclature.type_.value,
                category_id=nomenclature.category_id,
                created_at=nomenclature.created_at,
            )
        )

    async def save(self, nomenclature: Nomenclature) -> None:
        await self._session.execute(
            update(NOMENCLATURES_TABLE)
            .where(NOMENCLATURES_TABLE.c.id == nomenclature.id)
            .values(
                sku=nomenclature.sku,
                name=nomenclature.name,
                category_id=nomenclature.category_id,
            )
        )

    async def get_by_id(self, nomenclature_id: UUID) -> Nomenclature | None:
        stmt = select(NOMENCLATURES_TABLE).where(
            NOMENCLATURES_TABLE.c.id == nomenclature_id
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> Nomenclature:
        return Nomenclature(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            unit=UnitOfMeasurement(row["unit"]),
            type_=NomenclatureType(row["type"]),
            category_id=row["category_id"],
            created_at=row["created_at"],
        )
