from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent


class PosAgentRepository(ABC):
    @abstractmethod
    async def add(self, agent: PosAgent) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, agent: PosAgent) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, agent_id: UUID) -> PosAgent | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_key_hash(self, api_key_hash: str) -> PosAgent | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_source(self, source_id: UUID) -> list[PosAgent]:
        raise NotImplementedError
