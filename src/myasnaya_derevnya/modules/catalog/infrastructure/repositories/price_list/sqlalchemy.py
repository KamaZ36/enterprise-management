from uuid import UUID

from sqlalchemy import RowMapping, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.price_list import PriceList
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.base import (
    PriceListRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import PRICE_LISTS_TABLE


class SQLAlchemyPriceListRepository(PriceListRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, price_list: PriceList) -> None:
        await self._session.execute(
            insert(PRICE_LISTS_TABLE).values(
                id=price_list.id,
                name=price_list.name,
                created_at=price_list.created_at,
            )
        )

    async def save(self, price_list: PriceList) -> None:
        await self._session.execute(
            update(PRICE_LISTS_TABLE)
            .where(PRICE_LISTS_TABLE.c.id == price_list.id)
            .values(
                name=price_list.name,
            )
        )

    async def get_by_id(self, price_list_id: UUID) -> PriceList | None:
        stmt = select(PRICE_LISTS_TABLE).where(PRICE_LISTS_TABLE.c.id == price_list_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> PriceList:
        return PriceList(
            id_=row["id"],
            name=row["name"],
            created_at=row["created_at"],
        )
