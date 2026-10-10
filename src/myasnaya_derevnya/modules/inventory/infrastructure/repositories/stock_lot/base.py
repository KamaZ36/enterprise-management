from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot import StockLot


class StockLotRepository(ABC):
    @abstractmethod
    async def add(self, lot: StockLot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, lot_id: UUID) -> StockLot | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_code(
        self, nomenclature_id: UUID, lot_code: str
    ) -> StockLot | None:
        raise NotImplementedError
