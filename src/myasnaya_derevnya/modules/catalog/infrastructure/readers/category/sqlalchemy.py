from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.catalog.application.dto import CategoryListItem
from myasnaya_derevnya.modules.catalog.infrastructure.readers.category.base import (
    CategoryReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import CATEGORIES_TABLE


class SQLAlchemyCategoryReader(CategoryReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, search: str | None = None) -> list[CategoryListItem]:
        stmt = select(
            CATEGORIES_TABLE.c.id,
            CATEGORIES_TABLE.c.name,
            CATEGORIES_TABLE.c.parent_id,
        )

        if search:
            stmt = stmt.where(
                CATEGORIES_TABLE.c.name.ilike(like_pattern(search), escape="\\")
            )

        stmt = stmt.order_by(CATEGORIES_TABLE.c.name.asc())
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows]

    def _to_dto(self, row: RowMapping) -> CategoryListItem:
        return CategoryListItem(
            id=row["id"], name=row["name"], parent_id=row["parent_id"]
        )
