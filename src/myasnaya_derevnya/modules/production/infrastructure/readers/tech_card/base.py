from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.production.application.dto import TechCardListItem


class TechCardReader(ABC):
    @abstractmethod
    async def list(
        self, *, search: str | None, limit: int, offset: int
    ) -> tuple[list[TechCardListItem], int]:
        raise NotImplementedError
