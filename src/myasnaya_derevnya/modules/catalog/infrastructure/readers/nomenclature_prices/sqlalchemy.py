from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.application.dto import NomenclaturePriceItem
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.base import (
    NomenclaturePricesReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    PRICE_LISTS_TABLE,
    PRICES_TABLE,
)


class SQLAlchemyNomenclaturePricesReader(NomenclaturePricesReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_nomenclature(
        self, nomenclature_id: UUID
    ) -> list[NomenclaturePriceItem]:
        query = (
            select(
                PRICE_LISTS_TABLE.c.id,
                PRICE_LISTS_TABLE.c.name,
                PRICE_LISTS_TABLE.c.is_active,
                PRICES_TABLE.c.value,
            )
            .select_from(
                PRICE_LISTS_TABLE.outerjoin(
                    PRICES_TABLE,
                    and_(
                        PRICES_TABLE.c.price_list_id == PRICE_LISTS_TABLE.c.id,
                        PRICES_TABLE.c.nomenclature_id == nomenclature_id,
                    ),
                )
            )
            .order_by(PRICE_LISTS_TABLE.c.name.asc())
        )
        rows = (await self._session.execute(query)).mappings().all()

        return [
            NomenclaturePriceItem(
                price_list_id=row["id"],
                price_list_name=row["name"],
                is_active=row["is_active"],
                value=row["value"],
            )
            for row in rows
        ]
