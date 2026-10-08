from uuid import UUID

from sqlalchemy import RowMapping, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.category import Category
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.base import (
    CategoryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import CATEGORIES_TABLE


class SQLAlchemyCategoryRepository(CategoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, category: Category) -> None:
        await self._session.execute(
            insert(CATEGORIES_TABLE).values(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
            )
        )

    async def save(self, category: Category) -> None:
        await self._session.execute(
            update(CATEGORIES_TABLE)
            .where(CATEGORIES_TABLE.c.id == category.id)
            .values(
                name=category.name,
                parent_id=category.parent_id,
            )
        )

    async def get_by_id(self, category_id: UUID) -> Category | None:
        stmt = select(CATEGORIES_TABLE).where(CATEGORIES_TABLE.c.id == category_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def check_exists_by_id(self, category_id: UUID) -> bool:
        stmt = select(exists().where(CATEGORIES_TABLE.c.id == category_id))
        return bool((await self._session.execute(stmt)).scalar())

    async def check_exists_by_name(self, category_name: str) -> bool:
        stmt = select(exists().where(CATEGORIES_TABLE.c.name == category_name))
        return bool((await self._session.execute(stmt)).scalar())

    def _to_entity(self, row: RowMapping) -> Category:
        return Category(
            id_=row["id"],
            name=row["name"],
            parent_id=row["parent_id"],
        )
