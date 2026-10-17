from abc import ABC, abstractmethod
from collections.abc import Sequence
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
        search: str | None = None,
        nomenclature_ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LotBalanceListItem], int]:
        """Партионные остатки локации страницей.

        ``search`` ищет по коду партии, ``nomenclature_ids`` — предфильтр по
        номенклатуре (идентификаторы, найденные каталогом по названию/артикулу).
        Если задан ``search``, оба условия объединяются через ``OR``.
        """
        raise NotImplementedError
