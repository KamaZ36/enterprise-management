from abc import ABC, abstractmethod
from collections.abc import Mapping
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.opening_balance import (
    OpeningBalance,
)


class OpeningBalanceRepository(ABC):
    @abstractmethod
    async def add(self, opening_balance: OpeningBalance) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, opening_balance: OpeningBalance) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, opening_balance_id: UUID) -> OpeningBalance | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, opening_balance_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def attach_lot_ids(
        self, opening_balance_id: UUID, lot_ids: Mapping[UUID, UUID]
    ) -> None:
        """Проставляет ``lot_id`` в строках документа (line_id -> lot_id)."""
        raise NotImplementedError
