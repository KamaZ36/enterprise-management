from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.catalog.domain.entities.product import Product


class ProductRepository(ABC):
    """Product repository"""

    @abstractmethod
    async def add(self, product: Product) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, product_id: UUID) -> Product | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, product: Product) -> None:
        raise NotImplementedError
