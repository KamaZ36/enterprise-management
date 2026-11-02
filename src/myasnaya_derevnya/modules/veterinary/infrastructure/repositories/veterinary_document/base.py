from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.veterinary.domain.entities.veterinary_document import (
    VeterinaryDocument,
)


class VeterinaryDocumentRepository(ABC):
    @abstractmethod
    async def add(self, document: VeterinaryDocument) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> VeterinaryDocument | None:
        raise NotImplementedError
