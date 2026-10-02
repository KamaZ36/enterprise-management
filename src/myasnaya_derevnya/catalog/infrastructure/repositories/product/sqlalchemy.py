from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.catalog.domain.entities.product import Product, ProductType, Unit
from myasnaya_derevnya.catalog.infrastructure.repositories.product.base import (
    ProductRepository,
)
from myasnaya_derevnya.infrastructure.database.tables.product import PRODUCTS_TABLE


class SQLAlchemyProductRepository(ProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, product: Product) -> None:
        stmt = insert(PRODUCTS_TABLE).values(
            id=product.id,
            name=product.name,
            product_type=product.product_type.value,
            sku=product.sku,
            unit=product.unit.value,
            description=product.description,
            active=product.active,
        )
        await self._session.execute(stmt)

    async def get_by_id(self, product_id: UUID) -> Product | None:
        query = select(PRODUCTS_TABLE).where(PRODUCTS_TABLE.c.id == product_id)
        result = await self._session.execute(query)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def save(self, product: Product) -> None:
        stmt = (
            update(PRODUCTS_TABLE)
            .where(PRODUCTS_TABLE.c.id == product.id)
            .values(
                name=product.name,
                product_type=product.product_type.value,
                sku=product.sku,
                unit=product.unit.value,
                description=product.description,
                active=product.active,
            )
        )
        await self._session.execute(stmt)

    def _to_entity(self, row: RowMapping) -> Product:
        return Product(
            id=row["id"],
            name=row["name"],
            product_type=ProductType(row["product_type"]),
            sku=row["sku"],
            unit=Unit(row["unit"]),
            description=row["description"],
            active=row["active"],
        )
