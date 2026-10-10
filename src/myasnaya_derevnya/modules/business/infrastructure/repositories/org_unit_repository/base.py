from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnit


class OrgUnitRepository(ABC):
    @abstractmethod
    async def add(self, org_unit: OrgUnit) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, org_unit: OrgUnit) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, org_unit_id: UUID) -> OrgUnit | None:
        raise NotImplementedError

    @abstractmethod
    async def get_children(self, org_unit_id: UUID) -> list[OrgUnit]:
        raise NotImplementedError

    @abstractmethod
    async def ancestors_of(self, org_unit_id: UUID) -> frozenset[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def descendants_of(self, org_unit_id: UUID) -> frozenset[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def root_of(self, org_unit_id: UUID) -> UUID | None:
        raise NotImplementedError

    @abstractmethod
    async def get_root_id(self) -> UUID | None:
        raise NotImplementedError
