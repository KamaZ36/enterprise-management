from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.catalog.application.dto import NomenclatureListItem
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature.base import (
    NomenclatureReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    CATEGORIES_TABLE,
    NOMENCLATURES_TABLE,
)


class SQLAlchemyNomenclatureReader(NomenclatureReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        search: str | None = None,
        type_code: str | None = None,
        category_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NomenclatureListItem], int]:
        conditions = self._conditions(
            search=search, type_code=type_code, category_id=category_id
        )

        # Категория присоединяется только в выборке: на количество она не влияет,
        # потому что ссылка обязательная.
        total = await self._session.scalar(
            select(func.count()).select_from(NOMENCLATURES_TABLE).where(*conditions)
        )

        stmt = (
            select(
                NOMENCLATURES_TABLE.c.id,
                NOMENCLATURES_TABLE.c.sku,
                NOMENCLATURES_TABLE.c.name,
                NOMENCLATURES_TABLE.c.type,
                NOMENCLATURES_TABLE.c.unit,
                NOMENCLATURES_TABLE.c.category_id,
                CATEGORIES_TABLE.c.name.label("category_name"),
            )
            .join(
                CATEGORIES_TABLE,
                CATEGORIES_TABLE.c.id == NOMENCLATURES_TABLE.c.category_id,
            )
            .where(*conditions)
            .order_by(NOMENCLATURES_TABLE.c.name.asc(), NOMENCLATURES_TABLE.c.sku.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows], total or 0

    def _conditions(
        self,
        *,
        search: str | None,
        type_code: str | None,
        category_id: UUID | None,
    ) -> list:
        conditions: list = []

        if search:
            pattern = like_pattern(search)
            conditions.append(
                or_(
                    NOMENCLATURES_TABLE.c.name.ilike(pattern, escape="\\"),
                    NOMENCLATURES_TABLE.c.sku.ilike(pattern, escape="\\"),
                )
            )
        if type_code:
            conditions.append(NOMENCLATURES_TABLE.c.type == type_code)
        if category_id is not None:
            conditions.append(NOMENCLATURES_TABLE.c.category_id == category_id)

        return conditions

    def _to_dto(self, row: RowMapping) -> NomenclatureListItem:
        return NomenclatureListItem(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            type=NomenclatureType(row["type"]),
            unit=UnitOfMeasurement(row["unit"]),
            category_id=row["category_id"],
            category_name=row["category_name"],
        )
