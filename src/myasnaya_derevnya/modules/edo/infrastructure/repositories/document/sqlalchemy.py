from uuid import UUID

from sqlalchemy import RowMapping, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.edo.domain.entities.edo_document import EdoDocument
from myasnaya_derevnya.modules.edo.infrastructure.repositories.document.base import (
    EdoDocumentRepository,
)
from myasnaya_derevnya.modules.edo.infrastructure.tables import EDO_DOCUMENTS_TABLE


class SQLAlchemyEdoDocumentRepository(EdoDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: EdoDocument) -> None:
        await self._session.execute(
            insert(EDO_DOCUMENTS_TABLE).values(
                id=document.id,
                org_unit_id=document.org_unit_id,
                external_id=document.external_id,
                number=document.number,
                doc_date=document.doc_date,
                supplier_name=document.supplier_name,
                supplier_inn=document.supplier_inn,
                delivery_address=document.delivery_address,
                comment=document.comment,
                status=document.status,
                created_by=document.created_by,
                created_at=document.created_at,
            )
        )

    async def get_by_id(self, document_id: UUID) -> EdoDocument | None:
        stmt = select(EDO_DOCUMENTS_TABLE).where(
            EDO_DOCUMENTS_TABLE.c.id == document_id
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        return self._to_entity(row) if row is not None else None

    @staticmethod
    def _to_entity(row: RowMapping) -> EdoDocument:
        return EdoDocument(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            external_id=row["external_id"],
            number=row["number"],
            doc_date=row["doc_date"],
            supplier_name=row["supplier_name"],
            supplier_inn=row["supplier_inn"],
            delivery_address=row["delivery_address"],
            comment=row["comment"],
            status=row["status"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )
