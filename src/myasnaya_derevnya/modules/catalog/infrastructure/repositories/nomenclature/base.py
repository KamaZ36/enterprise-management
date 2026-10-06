from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import Nomenclature


class NomenclatureRepository(ABC):
    @abstractmethod
    def add(self, nomenclature: Nomenclature) -> None:
        raise NotImplementedError

    @abstractmethod
    def save(self, nomenclature: Nomenclature) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, nomenclature_id: UUID) -> Nomenclature | None:
        raise NotImplementedError
