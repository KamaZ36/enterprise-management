from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.production.application.dto import (
    ProductionOrderListItem,
)


class ProductionOrderReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None,
        statuses: Sequence[str] | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProductionOrderListItem], int]:
        raise NotImplementedError
