from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.inventory.application.dto import WarehouseListItem


class WarehouseReader(ABC):
    @abstractmethod
    async def list_all(self) -> list[WarehouseListItem]:
        raise NotImplementedError
