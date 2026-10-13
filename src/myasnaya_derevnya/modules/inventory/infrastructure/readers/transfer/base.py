from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    TransferDetail,
    TransferListItem,
)


class TransferReader(ABC):
    """Чтение перемещений для журнала и карточки."""

    @abstractmethod
    async def list(
        self,
        *,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TransferListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, transfer_id: UUID) -> TransferDetail | None:
        raise NotImplementedError
