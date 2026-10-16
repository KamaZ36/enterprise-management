from abc import ABC, abstractmethod
from collections.abc import Mapping
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.receipt import Receipt


class ReceiptRepository(ABC):
    @abstractmethod
    async def add(self, receipt: Receipt) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, receipt: Receipt) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, receipt_id: UUID) -> Receipt | None:
        raise NotImplementedError

    @abstractmethod
    async def attach_lot_ids(
        self, receipt_id: UUID, lot_ids: Mapping[UUID, UUID]
    ) -> None:
        """Проставляет ``lot_id`` в строках поступления (line_id -> lot_id)."""
        raise NotImplementedError
