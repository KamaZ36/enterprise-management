from dataclasses import dataclass

from myasnaya_derevnya.catalog.domain.entities.product import Product, ProductType, Unit
from myasnaya_derevnya.catalog.infrastructure.repositories.product.base import (
    ProductRepository,
)
from myasnaya_derevnya.core.database.transaction_manager.base import (
    TransactionManager,
)


@dataclass
class CreateProductCommand:
    name: str
    product_type: ProductType
    sku: int
    unit: Unit
    description: str


class CreateProductCommandInteractor:
    def __init__(
        self,
        product_repository: ProductRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._product_repository = product_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateProductCommand) -> None:
        product = Product.create(
            name=command.name,
            product_type=command.product_type,
            sku=command.sku,
            unit=command.unit,
            description=command.description,
        )

        await self._product_repository.add(product)
        await self._transaction_manager.commit()
