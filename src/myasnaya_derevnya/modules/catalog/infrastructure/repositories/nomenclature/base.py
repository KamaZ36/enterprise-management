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

    @abstractmethod
    async def get_names(self, nomenclature_ids: set[UUID]) -> dict[UUID, str]:
        raise NotImplementedError

    @abstractmethod
    async def get_ids_by_search(self, search: str, *, limit: int) -> list[UUID]:
        """Идентификаторы номенклатур, найденных по названию или артикулу."""
        raise NotImplementedError

    @abstractmethod
    async def get_id_by_gtin(self, gtin: str) -> UUID | None:
        """Идентификатор активной номенклатуры с указанным GTIN."""
        raise NotImplementedError
