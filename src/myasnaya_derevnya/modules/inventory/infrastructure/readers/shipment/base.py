from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    ShipmentDetail,
    ShipmentListItem,
)


class ShipmentReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ShipmentListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, shipment_id: UUID) -> ShipmentDetail | None:
        raise NotImplementedError
