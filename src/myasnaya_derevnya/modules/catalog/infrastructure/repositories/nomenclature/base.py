from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import Nomenclature


class NomenclatureRepository(ABC):
    @abstractmethod
    async def add(self, nomenclature: Nomenclature) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, nomenclature: Nomenclature) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, nomenclature_id: UUID) -> Nomenclature | None:
        raise NotImplementedError
