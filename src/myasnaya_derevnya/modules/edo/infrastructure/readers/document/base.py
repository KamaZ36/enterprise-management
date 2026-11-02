from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.edo.application.dto import EdoDocumentListItem


class EdoDocumentReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_id: UUID,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EdoDocumentListItem], int]:
        raise NotImplementedError
