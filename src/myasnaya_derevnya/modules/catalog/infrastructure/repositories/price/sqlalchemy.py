from uuid import UUID

from sqlalchemy import RowMapping, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.price import Price
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.base import (
    PriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import PRICES_TABLE


class SQLAlchemyPriceRepository(PriceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, price: Price) -> None:
        await self._session.execute(
            insert(PRICES_TABLE).values(
                id=price.id,
                nomenclature_id=price.nomenclature_id,
                price_list_id=price.price_list_id,
                value=price.value,
                updated_at=price.updated_at,
            )
        )

    async def save(self, price: Price) -> None:
        await self._session.execute(
            update(PRICES_TABLE)
            .where(PRICES_TABLE.c.id == price.id)
            .values(
                value=price.value,
                updated_at=price.updated_at,
            )
        )

    async def get_by_nomenclature_and_list(
        self, nomenclature_id: UUID, price_list_id: UUID
    ) -> Price | None:
        stmt = select(PRICES_TABLE).where(
            PRICES_TABLE.c.nomenclature_id == nomenclature_id,
            PRICES_TABLE.c.price_list_id == price_list_id,
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_by_id(self, price_id: UUID) -> Price | None:
        stmt = select(PRICES_TABLE).where(PRICES_TABLE.c.id == price_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> Price:
        return Price(
            id_=row["id"],
            nomenclature_id=row["nomenclature_id"],
            price_list_id=row["price_list_id"],
            value=row["value"],
            updated_at=row["updated_at"],
        )
