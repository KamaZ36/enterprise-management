from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.catalog.application.dto import StopListItem


class StopListReader(ABC):
    @abstractmethod
    async def list_by_org_unit(self, org_unit_id: UUID) -> list[StopListItem]:
        raise NotImplementedError

    @abstractmethod
    async def stopped_nomenclature_ids(
        self, org_unit_id: UUID, nomenclature_ids: Iterable[UUID]
    ) -> set[UUID]:
        raise NotImplementedError
