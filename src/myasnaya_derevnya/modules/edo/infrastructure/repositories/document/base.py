from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.edo.domain.entities.edo_document import EdoDocument


class EdoDocumentRepository(ABC):
    @abstractmethod
    async def add(self, document: EdoDocument) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> EdoDocument | None:
        raise NotImplementedError
