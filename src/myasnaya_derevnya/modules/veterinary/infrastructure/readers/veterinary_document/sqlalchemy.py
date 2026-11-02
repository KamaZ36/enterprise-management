from uuid import UUID

from sqlalchemy import RowMapping, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.veterinary.application.dto import (
    VeterinaryDocumentListItem,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.readers.veterinary_document.base import (
    VeterinaryDocumentReader,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.tables import (
    VETERINARY_DOCUMENTS_TABLE,
)


class SQLAlchemyVeterinaryDocumentReader(VeterinaryDocumentReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_id: UUID,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[VeterinaryDocumentListItem], int]:
        conditions = [VETERINARY_DOCUMENTS_TABLE.c.org_unit_id == org_unit_id]

        if search:
            pattern = like_pattern(search)
            conditions.append(
                or_(
                    VETERINARY_DOCUMENTS_TABLE.c.number.ilike(
                        pattern, escape="\\"
                    ),
                    VETERINARY_DOCUMENTS_TABLE.c.batch_id.ilike(
                        pattern, escape="\\"
                    ),
                    cast(VETERINARY_DOCUMENTS_TABLE.c.guid, String).ilike(
                        pattern, escape="\\"
                    ),
                )
            )

        total = await self._session.scalar(
            select(func.count())
            .select_from(VETERINARY_DOCUMENTS_TABLE)
            .where(*conditions)
        )

        stmt = (
            select(VETERINARY_DOCUMENTS_TABLE)
            .where(*conditions)
            .order_by(
                VETERINARY_DOCUMENTS_TABLE.c.created_at.desc(),
                VETERINARY_DOCUMENTS_TABLE.c.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows], int(total or 0)

    @staticmethod
    def _to_dto(row: RowMapping) -> VeterinaryDocumentListItem:
        return VeterinaryDocumentListItem(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            number=row["number"],
            guid=row["guid"],
            batch_id=row["batch_id"],
            product_item_guid=row["product_item_guid"],
            source=row["source"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )
