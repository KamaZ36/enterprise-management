from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import LotBalanceListItem


class LotBalanceReader(ABC):
    @abstractmethod
    async def list_by_org_unit(
        self,
        org_unit_id: UUID,
        *,
        with_cost: bool,
        include_empty: bool = False,
        expiring_before: date | None = None,
    ) -> list[LotBalanceListItem]:
        raise NotImplementedError
