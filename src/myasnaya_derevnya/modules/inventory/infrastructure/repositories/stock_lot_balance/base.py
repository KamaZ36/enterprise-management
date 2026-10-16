from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot_balance import (
    StockLotBalance,
)

LotBalanceKey = tuple[UUID, UUID, UUID]


class StockLotBalanceRepository(ABC):
    @abstractmethod
    async def lock_many(
        self, keys: Iterable[LotBalanceKey]
    ) -> dict[LotBalanceKey, StockLotBalance]:
        raise NotImplementedError

    @abstractmethod
    async def save_many(self, balances: Sequence[StockLotBalance]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_available(
        self, warehouse_id: UUID, nomenclature_id: UUID
    ) -> list[StockLotBalance]:
        """Блокирует и возвращает партии с остатком в порядке FEFO."""
        raise NotImplementedError
