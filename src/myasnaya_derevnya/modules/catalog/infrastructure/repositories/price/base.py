from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.price import Price


class PriceRepository(ABC):
    @abstractmethod
    async def add(self, price: Price) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, price: Price) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_nomenclature_and_list(
        self, nomenclature_id: UUID, price_list_id: UUID
    ) -> Price | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, price_id: UUID) -> Price | None:
        raise NotImplementedError
