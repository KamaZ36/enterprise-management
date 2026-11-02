from uuid import UUID

from myasnaya_derevnya.modules.edo.application.dto import EdoDocumentInfo
from myasnaya_derevnya.modules.edo.infrastructure.repositories.document.base import (
    EdoDocumentRepository,
)


class EdoAPI:
    """Фасад ЭДО для других модулей."""

    def __init__(self, document_repository: EdoDocumentRepository) -> None:
        self._document_repository = document_repository

    async def get_document(self, document_id: UUID) -> EdoDocumentInfo | None:
        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            return None

        return EdoDocumentInfo(
            id=document.id,
            org_unit_id=document.org_unit_id,
            number=document.number,
        )
