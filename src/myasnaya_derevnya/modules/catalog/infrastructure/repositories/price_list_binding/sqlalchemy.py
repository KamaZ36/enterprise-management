from uuid import UUID

from sqlalchemy import RowMapping, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.base import (
    PriceListBindingRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    PRICE_LIST_BINDINGS_TABLE,
)


class SQLAlchemyPriceListBindingRepository(PriceListBindingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, binding: PriceListBinding) -> None:
        stmt = insert(PRICE_LIST_BINDINGS_TABLE).values(
            id=binding.id,
            org_unit_id=binding.org_unit_id,
            price_list_id=binding.price_list_id,
            created_at=binding.created_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[PRICE_LIST_BINDINGS_TABLE.c.org_unit_id],
            set_={"price_list_id": stmt.excluded.price_list_id},
        )
        await self._session.execute(stmt)

    async def get_by_org_unit(self, org_unit_id: UUID) -> PriceListBinding | None:
        query = select(PRICE_LIST_BINDINGS_TABLE).where(
            PRICE_LIST_BINDINGS_TABLE.c.org_unit_id == org_unit_id
        )
        row = (await self._session.execute(query)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> PriceListBinding:
        return PriceListBinding(
            id_=row["id"],
            org_unit_id=row["org_unit_id"],
            price_list_id=row["price_list_id"],
            created_at=row["created_at"],
        )
