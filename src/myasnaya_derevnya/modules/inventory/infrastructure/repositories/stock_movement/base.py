from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    StockMovement,
)


class StockMovementRepository(ABC):
    @abstractmethod
    async def count_for_nomenclature(self, nomenclature_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def add_many(self, movements: Sequence[StockMovement]) -> None:
        raise NotImplementedError
