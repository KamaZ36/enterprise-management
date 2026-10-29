from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.domain.entities.product_mapping import (
    PosProductMapping,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.base import (
    PosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import (
    POS_PRODUCT_MAP_TABLE,
)


class SQLAlchemyPosProductMapRepository(PosProductMapRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, mapping_id: UUID) -> PosProductMapping | None:
        row = (
            (
                await self._session.execute(
                    select(POS_PRODUCT_MAP_TABLE).where(
                        POS_PRODUCT_MAP_TABLE.c.id == mapping_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        return self._to_entity(row) if row is not None else None

    async def get_by_source_product(
        self, source_id: UUID, doka_product_guid: str
    ) -> PosProductMapping | None:
        row = (
            (
                await self._session.execute(
                    select(POS_PRODUCT_MAP_TABLE).where(
                        POS_PRODUCT_MAP_TABLE.c.source_id == source_id,
                        POS_PRODUCT_MAP_TABLE.c.doka_product_guid == doka_product_guid,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        return self._to_entity(row) if row is not None else None

    async def mappings_for(
        self, source_id: UUID, product_guids: Iterable[str]
    ) -> dict[str, PosProductMapping]:
        guids = list(dict.fromkeys(product_guids))
        if not guids:
            return {}

        rows = (
            (
                await self._session.execute(
                    select(POS_PRODUCT_MAP_TABLE).where(
                        POS_PRODUCT_MAP_TABLE.c.source_id == source_id,
                        POS_PRODUCT_MAP_TABLE.c.doka_product_guid.in_(guids),
                        POS_PRODUCT_MAP_TABLE.c.is_active.is_(True),
                    )
                )
            )
            .mappings()
            .all()
        )

        return {
            row["doka_product_guid"]: self._to_entity(row) for row in rows
        }

    async def list_by_source(
        self, source_id: UUID, *, search: str | None = None
    ) -> list[PosProductMapping]:
        stmt = select(POS_PRODUCT_MAP_TABLE).where(
            POS_PRODUCT_MAP_TABLE.c.source_id == source_id
        )

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                POS_PRODUCT_MAP_TABLE.c.doka_product_guid.ilike(pattern)
            )

        stmt = stmt.order_by(POS_PRODUCT_MAP_TABLE.c.updated_at.desc())
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_entity(row) for row in rows]

    async def upsert(self, mapping: PosProductMapping) -> UUID:
        stmt = (
            pg_insert(POS_PRODUCT_MAP_TABLE)
            .values(
                id=mapping.id,
                source_id=mapping.source_id,
                doka_product_guid=mapping.doka_product_guid,
                nomenclature_id=mapping.nomenclature_id,
                unit_factor=mapping.unit_factor,
                is_active=mapping.is_active,
                created_by=mapping.created_by,
                created_at=mapping.created_at,
                updated_at=mapping.updated_at,
            )
            .on_conflict_do_update(
                constraint="uq_pos_product_map_source_product",
                set_={
                    "nomenclature_id": mapping.nomenclature_id,
                    "unit_factor": mapping.unit_factor,
                    "is_active": mapping.is_active,
                    "updated_at": func.now(),
                },
            )
            .returning(POS_PRODUCT_MAP_TABLE.c.id)
        )

        return (await self._session.execute(stmt)).scalar_one()

    async def delete(self, mapping_id: UUID) -> None:
        await self._session.execute(
            delete(POS_PRODUCT_MAP_TABLE).where(
                POS_PRODUCT_MAP_TABLE.c.id == mapping_id
            )
        )

    @staticmethod
    def _to_entity(row) -> PosProductMapping:
        return PosProductMapping(
            id=row["id"],
            source_id=row["source_id"],
            doka_product_guid=row["doka_product_guid"],
            nomenclature_id=row["nomenclature_id"],
            unit_factor=row["unit_factor"],
            is_active=row["is_active"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
