from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot import StockLot


class StockLotRepository(ABC):
    @abstractmethod
    async def add(self, lot: StockLot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, lot: StockLot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, lot_id: UUID) -> StockLot | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_identity(
        self,
        nomenclature_id: UUID,
        lot_code: str,
        produced_at: date | None,
        supplier_name: str | None,
    ) -> StockLot | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_code(
        self, nomenclature_id: UUID, lot_code: str
    ) -> list[StockLot]:
        raise NotImplementedError
