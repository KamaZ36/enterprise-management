from uuid import UUID

from sqlalchemy import RowMapping, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.veterinary.domain.entities.veterinary_document import (
    VeterinaryDocument,
    VeterinaryDocumentSource,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.repositories.veterinary_document.base import (
    VeterinaryDocumentRepository,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.tables import (
    VETERINARY_DOCUMENTS_TABLE,
)


class SQLAlchemyVeterinaryDocumentRepository(VeterinaryDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: VeterinaryDocument) -> None:
        await self._session.execute(
            insert(VETERINARY_DOCUMENTS_TABLE).values(
                id=document.id,
                org_unit_id=document.org_unit_id,
                number=document.number,
                guid=document.guid,
                batch_id=document.batch_id,
                product_item_guid=document.product_item_guid,
                source=document.source.value,
                created_by=document.created_by,
                created_at=document.created_at,
            )
        )

    async def get_by_id(self, document_id: UUID) -> VeterinaryDocument | None:
        stmt = select(VETERINARY_DOCUMENTS_TABLE).where(
            VETERINARY_DOCUMENTS_TABLE.c.id == document_id
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        return self._to_entity(row) if row is not None else None

    @staticmethod
    def _to_entity(row: RowMapping) -> VeterinaryDocument:
        return VeterinaryDocument(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            number=row["number"],
            guid=row["guid"],
            batch_id=row["batch_id"],
            product_item_guid=row["product_item_guid"],
            source=VeterinaryDocumentSource(row["source"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
        )
