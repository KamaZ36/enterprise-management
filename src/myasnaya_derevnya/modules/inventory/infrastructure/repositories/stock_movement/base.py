from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
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

    @abstractmethod
    async def list_by_posting(self, posting_id: UUID) -> list[StockMovement]:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_posting(self, posting_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def has_later_movements(
        self,
        *,
        posting_id: UUID,
        since: datetime,
        org_unit_id: UUID,
        nomenclature_id: UUID,
    ) -> bool:
        raise NotImplementedError
