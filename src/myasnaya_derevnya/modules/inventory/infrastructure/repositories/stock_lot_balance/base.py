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
        """Партионные остатки по ключам, с созданием отсутствующих и блокировкой."""
        raise NotImplementedError

    @abstractmethod
    async def save_many(self, balances: Sequence[StockLotBalance]) -> None:
        raise NotImplementedError
