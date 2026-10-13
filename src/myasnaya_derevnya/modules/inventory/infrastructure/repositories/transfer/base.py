from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.transfer import Transfer


class TransferRepository(ABC):
    @abstractmethod
    async def add(self, transfer: Transfer) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, transfer: Transfer) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, transfer_id: UUID) -> Transfer | None:
        raise NotImplementedError
