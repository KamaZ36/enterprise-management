from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem


class BalanceReader(ABC):
    @abstractmethod
    async def list_by_org_unit(
        self, org_unit_id: UUID, *, with_cost: bool
    ) -> list[BalanceListItem]:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self, org_unit_id: UUID, nomenclature_id: UUID, *, with_cost: bool
    ) -> BalanceListItem | None:
        raise NotImplementedError
