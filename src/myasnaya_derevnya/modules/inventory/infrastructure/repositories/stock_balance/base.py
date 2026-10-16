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
        raise NotImplementedError

    @abstractmethod
    async def save_many(self, balances: Sequence[StockBalance]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self, org_unit_id: UUID, nomenclature_id: UUID
    ) -> StockBalance | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_org_unit(self, org_unit_id: UUID) -> list[StockBalance]:
        raise NotImplementedError
