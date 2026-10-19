from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.inventory_count import (
    InventoryCount,
)


class InventoryCountRepository(ABC):
    @abstractmethod
    async def add(self, inventory_count: InventoryCount) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, inventory_count: InventoryCount) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, inventory_count_id: UUID) -> InventoryCount | None:
        raise NotImplementedError
