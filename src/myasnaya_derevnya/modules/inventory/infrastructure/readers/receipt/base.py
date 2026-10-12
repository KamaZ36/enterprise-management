from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    ReceiptDetail,
    ReceiptListItem,
)


class ReceiptReader(ABC):
    """Чтение поступлений для журнала и карточки."""

    @abstractmethod
    async def list(
        self,
        *,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ReceiptListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, receipt_id: UUID) -> ReceiptDetail | None:
        raise NotImplementedError
