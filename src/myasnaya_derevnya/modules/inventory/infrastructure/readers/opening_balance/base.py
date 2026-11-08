from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    OpeningBalanceDetail,
    OpeningBalanceListItem,
)


class OpeningBalanceReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OpeningBalanceListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, opening_balance_id: UUID) -> OpeningBalanceDetail | None:
        raise NotImplementedError
