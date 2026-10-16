from uuid import UUID

from sqlalchemy import RowMapping, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
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
                category_id=nomenclature.category_id,
                is_active=nomenclature.is_active,
                image_url=nomenclature.image_url,
                description=nomenclature.description,
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
                unit=nomenclature.unit.value,
                is_active=nomenclature.is_active,
                image_url=nomenclature.image_url,
                description=nomenclature.description,
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

    async def get_names(self, nomenclature_ids: set[UUID]) -> dict[UUID, str]:
        if not nomenclature_ids:
            return {}

        stmt = select(NOMENCLATURES_TABLE.c.id, NOMENCLATURES_TABLE.c.name).where(
            NOMENCLATURES_TABLE.c.id.in_(nomenclature_ids)
        )
        rows = (await self._session.execute(stmt)).all()

        return {row[0]: row[1] for row in rows}

    def _to_entity(self, row: RowMapping) -> Nomenclature:
        return Nomenclature(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            unit=UnitOfMeasurement(row["unit"]),
            category_id=row["category_id"],
            created_at=row["created_at"],
            is_active=row["is_active"],
            image_url=row["image_url"],
            description=row["description"],
        )
