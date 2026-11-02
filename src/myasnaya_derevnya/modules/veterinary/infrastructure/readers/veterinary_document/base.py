from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.veterinary.application.dto import (
    VeterinaryDocumentListItem,
)


class VeterinaryDocumentReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_id: UUID,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[VeterinaryDocumentListItem], int]:
        raise NotImplementedError
