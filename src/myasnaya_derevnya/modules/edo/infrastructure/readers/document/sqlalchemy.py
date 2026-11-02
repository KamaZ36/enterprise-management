from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.edo.application.dto import EdoDocumentListItem
from myasnaya_derevnya.modules.edo.infrastructure.readers.document.base import (
    EdoDocumentReader,
)
from myasnaya_derevnya.modules.edo.infrastructure.tables import EDO_DOCUMENTS_TABLE


class SQLAlchemyEdoDocumentReader(EdoDocumentReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_id: UUID,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EdoDocumentListItem], int]:
        conditions = [EDO_DOCUMENTS_TABLE.c.org_unit_id == org_unit_id]

        if search:
            pattern = like_pattern(search)
            conditions.append(
                or_(
                    EDO_DOCUMENTS_TABLE.c.number.ilike(pattern, escape="\\"),
                    EDO_DOCUMENTS_TABLE.c.external_id.ilike(
                        pattern, escape="\\"
                    ),
                    EDO_DOCUMENTS_TABLE.c.supplier_name.ilike(
                        pattern, escape="\\"
                    ),
                )
            )

        total = await self._session.scalar(
            select(func.count()).select_from(EDO_DOCUMENTS_TABLE).where(*conditions)
        )

        stmt = (
            select(EDO_DOCUMENTS_TABLE)
            .where(*conditions)
            .order_by(
                EDO_DOCUMENTS_TABLE.c.created_at.desc(),
                EDO_DOCUMENTS_TABLE.c.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows], int(total or 0)

    @staticmethod
    def _to_dto(row: RowMapping) -> EdoDocumentListItem:
        return EdoDocumentListItem(
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
