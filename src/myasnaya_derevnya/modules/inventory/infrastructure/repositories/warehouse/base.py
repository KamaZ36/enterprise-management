from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import Warehouse


class WarehouseRepository(ABC):
    @abstractmethod
    async def add(self, warehouse: Warehouse) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, warehouse: Warehouse) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_code(self, code: str) -> Warehouse | None:
        raise NotImplementedError

    @abstractmethod
    async def list(self) -> list[Warehouse]:
        raise NotImplementedError
