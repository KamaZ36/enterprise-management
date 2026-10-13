from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)


class PriceListBindingRepository(ABC):
    @abstractmethod
    async def save(self, binding: PriceListBinding) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_org_unit(self, org_unit_id: UUID) -> PriceListBinding | None:
        raise NotImplementedError
