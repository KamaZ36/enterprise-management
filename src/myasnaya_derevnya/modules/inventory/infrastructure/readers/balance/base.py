from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem


class BalanceReader(ABC):
    @abstractmethod
    async def list_by_org_unit(
        self,
        org_unit_id: UUID,
        *,
        with_cost: bool,
        nomenclature_ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BalanceListItem], int]:
        """Остатки локации страницей.

        ``nomenclature_ids`` — предфильтр по номенклатуре: ``None`` — без
        ограничения, пустой список — ничего не подходит.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self, org_unit_id: UUID, nomenclature_id: UUID, *, with_cost: bool
    ) -> BalanceListItem | None:
        raise NotImplementedError
