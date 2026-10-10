from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.receipt import Receipt


class ReceiptRepository(ABC):
    @abstractmethod
    async def add(self, receipt: Receipt) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, receipt: Receipt) -> None:
        """Сохраняет шапку. Строки после создания неизменяемы."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, receipt_id: UUID) -> Receipt | None:
        raise NotImplementedError
