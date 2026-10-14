from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.catalog.application.dto import (
    AssortmentItem,
    PriceListEntry,
    PriceListPriceItem,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.base import (
    NomenclaturePricesReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    CATEGORIES_TABLE,
    NOMENCLATURES_TABLE,
    PRICE_LISTS_TABLE,
    PRICES_TABLE,
)


class SQLAlchemyPriceListsReader(NomenclaturePricesReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_nomenclature(
        self, nomenclature_id: UUID
    ) -> list[PriceListPriceItem]:  # pragma: no cover - не используется
        raise NotImplementedError

    async def list_price_lists(self) -> list[PriceListEntry]:
        rows = (
            (
                await self._session.execute(
                    select(
                        PRICE_LISTS_TABLE.c.id,
                        PRICE_LISTS_TABLE.c.name,
                        PRICE_LISTS_TABLE.c.is_active,
                    ).order_by(PRICE_LISTS_TABLE.c.name.asc())
                )
            )
            .mappings()
            .all()
        )

        return [
            PriceListEntry(id=row["id"], name=row["name"], is_active=row["is_active"])
            for row in rows
        ]

    async def list_assortment(self, price_list_id: UUID) -> list[AssortmentItem]:
        stmt = (
            select(
                NOMENCLATURES_TABLE.c.id,
                NOMENCLATURES_TABLE.c.name,
                NOMENCLATURES_TABLE.c.sku,
                NOMENCLATURES_TABLE.c.unit,
                NOMENCLATURES_TABLE.c.category_id,
                NOMENCLATURES_TABLE.c.image_url,
                NOMENCLATURES_TABLE.c.description,
                CATEGORIES_TABLE.c.name.label("category_name"),
                PRICES_TABLE.c.value,
            )
            .select_from(
                NOMENCLATURES_TABLE.join(
                    PRICES_TABLE,
                    and_(
                        PRICES_TABLE.c.nomenclature_id == NOMENCLATURES_TABLE.c.id,
                        PRICES_TABLE.c.price_list_id == price_list_id,
                    ),
                )
                .join(
                    PRICE_LISTS_TABLE,
                    PRICE_LISTS_TABLE.c.id == PRICES_TABLE.c.price_list_id,
                )
                .join(
                    CATEGORIES_TABLE,
                    CATEGORIES_TABLE.c.id == NOMENCLATURES_TABLE.c.category_id,
                )
            )
            .where(
                NOMENCLATURES_TABLE.c.is_active.is_(True),
                PRICE_LISTS_TABLE.c.is_active.is_(True),
            )

            .order_by(
                CATEGORIES_TABLE.c.sort_order.asc(),
                NOMENCLATURES_TABLE.c.name.asc(),
            )
        )

        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            AssortmentItem(
                nomenclature_id=row["id"],
                name=row["name"],
                sku=row["sku"],
                unit=UnitOfMeasurement(row["unit"]),
                value=row["value"],
                category_id=row["category_id"],
                category_name=row["category_name"],
                image_url=row["image_url"],
                description=row["description"],
            )
            for row in rows
        ]

    async def list_by_price_list(
        self,
        price_list_id: UUID,
        *,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PriceListPriceItem], int]:
        conditions = []
        if search:
            conditions.extend(
                or_(
                    NOMENCLATURES_TABLE.c.name.ilike(like_pattern(token), escape="\\"),
                    NOMENCLATURES_TABLE.c.sku.ilike(like_pattern(token), escape="\\"),
                )
                for token in search.split()
            )

        join = NOMENCLATURES_TABLE.outerjoin(
            PRICES_TABLE,
            and_(
                PRICES_TABLE.c.nomenclature_id == NOMENCLATURES_TABLE.c.id,
                PRICES_TABLE.c.price_list_id == price_list_id,
            ),
        )

        total = await self._session.scalar(
            select(func.count()).select_from(NOMENCLATURES_TABLE).where(*conditions)
        )

        rows = (
            (
                await self._session.execute(
                    select(
                        NOMENCLATURES_TABLE.c.id,
                        NOMENCLATURES_TABLE.c.name,
                        NOMENCLATURES_TABLE.c.sku,
                        PRICES_TABLE.c.value,
                    )
                    .select_from(join)
                    .where(*conditions)
                    .order_by(NOMENCLATURES_TABLE.c.name.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        return (
            [
                PriceListPriceItem(
                    nomenclature_id=row["id"],
                    nomenclature_name=row["name"],
                    sku=row["sku"],
                    value=row["value"],
                )
                for row in rows
            ],
            int(total or 0),
        )
