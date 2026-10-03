from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.organization.domain.entities.location import Location


class LocationRepository(ABC):
    @abstractmethod
    async def add(self, location: Location) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, location_id: UUID) -> Location | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, location: Location) -> None:
        raise NotImplementedError
