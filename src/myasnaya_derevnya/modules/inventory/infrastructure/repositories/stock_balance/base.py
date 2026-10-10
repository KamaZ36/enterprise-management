from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_balance import (
    StockBalance,
)

BalanceKey = tuple[UUID, UUID]


class StockBalanceRepository(ABC):
    @abstractmethod
    async def lock_many(
        self, keys: Iterable[BalanceKey]
    ) -> dict[BalanceKey, StockBalance]:
        """Возвращает балансы по ключам, создавая отсутствующие и блокируя их.

        Блокировки берутся в отсортированном порядке ключей, иначе два
        параллельных перемещения между складами поймают дедлок.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_many(self, balances: Sequence[StockBalance]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self, warehouse_id: UUID, nomenclature_id: UUID
    ) -> StockBalance | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_warehouse(self, warehouse_id: UUID) -> list[StockBalance]:
        raise NotImplementedError
