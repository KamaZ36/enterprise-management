from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)


class DocumentNumberRepository(ABC):
    @abstractmethod
    async def next_sequence(
        self, document_type: DocumentType, year: int
    ) -> int:
        """Возвращает следующий номер в сквозной нумерации за год."""

        raise NotImplementedError
