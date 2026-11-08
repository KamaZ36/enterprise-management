from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_posting import (
    StockPosting,
)


class StockPostingRepository(ABC):
    @abstractmethod
    async def add(self, posting: StockPosting) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, *, document_type: str, document_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_by_document(
        self, *, document_type: str, document_id: UUID
    ) -> StockPosting | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, posting_id: UUID) -> None:
        raise NotImplementedError
