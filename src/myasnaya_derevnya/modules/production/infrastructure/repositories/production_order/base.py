from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
)


class ProductionOrderRepository(ABC):
    @abstractmethod
    async def add(self, order: ProductionOrder) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, order: ProductionOrder) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> ProductionOrder | None:
        raise NotImplementedError
