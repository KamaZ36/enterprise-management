from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource


class PosSourceRepository(ABC):
    @abstractmethod
    async def add(self, source: PosSource) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, source: PosSource) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, source_id: UUID) -> PosSource | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_doka_org_id(self, doka_org_id: str) -> PosSource | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[PosSource]:
        raise NotImplementedError
