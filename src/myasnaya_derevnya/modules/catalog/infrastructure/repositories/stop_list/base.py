from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.stop_list_entry import (
    StopListEntry,
)


class StopListEntryRepository(ABC):
    @abstractmethod
    async def add(self, entry: StopListEntry) -> bool:
        """Добавить товар в стоп-лист. False — уже был в стопе."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, org_unit_id: UUID, nomenclature_id: UUID) -> bool:
        """Убрать товар из стоп-листа. False — записи не было."""
        raise NotImplementedError
