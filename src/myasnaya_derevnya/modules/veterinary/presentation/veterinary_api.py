from uuid import UUID

from myasnaya_derevnya.modules.veterinary.domain.entities.veterinary_document import (
    VeterinaryDocument,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.repositories.veterinary_document.base import (
    VeterinaryDocumentRepository,
)


class VeterinaryAPI:
    """Фасад ветеринарного модуля для других модулей."""

    def __init__(self, document_repository: VeterinaryDocumentRepository) -> None:
        self._document_repository = document_repository

    async def create_manual_document(
        self,
        *,
        org_unit_id: UUID,
        number: str | None = None,
        guid: UUID | None = None,
        batch_id: str | None = None,
        product_item_guid: UUID | None = None,
        created_by: UUID | None = None,
    ) -> UUID:
        """Создаёт ручной ВСД в текущей транзакции вызывающего модуля."""
        document = VeterinaryDocument.create(
            org_unit_id=org_unit_id,
            number=number,
            guid=guid,
            batch_id=batch_id,
            product_item_guid=product_item_guid,
            created_by=created_by,
        )
        await self._document_repository.add(document)

        return document.id

    async def document_exists(self, document_id: UUID) -> bool:
        return await self._document_repository.get_by_id(document_id) is not None
