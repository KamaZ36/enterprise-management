from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.application.dto import NomenclatureListItem


class NomenclatureReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        search: str | None = None,
        type_code: str | None = None,
        category_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NomenclatureListItem], int]:
        raise NotImplementedError
