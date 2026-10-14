from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.production.application.dto import TechCardListItem
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.tech_card.base import (
    TechCardReader,
)
from myasnaya_derevnya.modules.production.infrastructure.tables import (
    TECH_CARD_LINES_TABLE,
    TECH_CARDS_TABLE,
)


class SQLAlchemyTechCardReader(TechCardReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, search: str | None, limit: int, offset: int
    ) -> tuple[list[TechCardListItem], int]:
        conditions = []

        if search:
            conditions.extend(
                or_(
                    TECH_CARDS_TABLE.c.code.ilike(
                        like_pattern(token), escape="\\"
                    ),
                    TECH_CARDS_TABLE.c.name.ilike(
                        like_pattern(token), escape="\\"
                    ),
                )
                for token in search.split()
            )

        total = await self._session.scalar(
            select(func.count()).select_from(TECH_CARDS_TABLE).where(*conditions)
        )

        line_counts = (
            select(
                TECH_CARD_LINES_TABLE.c.tech_card_id,
                func.count().label("line_count"),
            )
            .group_by(TECH_CARD_LINES_TABLE.c.tech_card_id)
            .subquery()
        )

        rows = (
            (
                await self._session.execute(
                    select(
                        TECH_CARDS_TABLE.c.id,
                        TECH_CARDS_TABLE.c.code,
                        TECH_CARDS_TABLE.c.version,
                        TECH_CARDS_TABLE.c.name,
                        TECH_CARDS_TABLE.c.basis,
                        TECH_CARDS_TABLE.c.valid_from,
                        TECH_CARDS_TABLE.c.comment,
                        TECH_CARDS_TABLE.c.created_at,
                        func.coalesce(line_counts.c.line_count, 0).label(
                            "line_count"
                        ),
                    )
                    .select_from(
                        TECH_CARDS_TABLE.outerjoin(
                            line_counts,
                            line_counts.c.tech_card_id == TECH_CARDS_TABLE.c.id,
                        )
                    )
                    .where(*conditions)
                    .order_by(
                        TECH_CARDS_TABLE.c.code.asc(),
                        TECH_CARDS_TABLE.c.version.desc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        return (
            [
                TechCardListItem(
                    id=row["id"],
                    code=row["code"],
                    version=row["version"],
                    name=row["name"],
                    basis=TechCardBasis(row["basis"]),
                    created_at=row["created_at"],
                    line_count=int(row["line_count"]),
                    valid_from=row["valid_from"],
                    comment=row["comment"],
                )
                for row in rows
            ],
            int(total or 0),
        )
