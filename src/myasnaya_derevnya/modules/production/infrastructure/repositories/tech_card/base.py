from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.production.domain.entities.tech_card import TechCard


class TechCardRepository(ABC):
    @abstractmethod
    async def add(self, tech_card: TechCard) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, tech_card_id: UUID) -> TechCard | None:
        raise NotImplementedError

    @abstractmethod
    async def next_version(self, code: str) -> int:
        raise NotImplementedError
