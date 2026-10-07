from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.price_list import PriceList


class PriceListRepository(ABC):
    @abstractmethod
    async def add(self, price_list: PriceList) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, price_list: PriceList) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, price_list_id: UUID) -> PriceList | None:
        raise NotImplementedError
