from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import (
    OpeningBalanceDetail,
    OpeningBalanceLineItem,
    OpeningBalanceListItem,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.opening_balance.base import (
    OpeningBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    OPENING_BALANCE_LINES_TABLE,
    OPENING_BALANCES_TABLE,
)


class SQLAlchemyOpeningBalanceReader(OpeningBalanceReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OpeningBalanceListItem], int]:
        conditions = []
        if org_unit_ids is not None:
            conditions.append(OPENING_BALANCES_TABLE.c.org_unit_id.in_(org_unit_ids))

        if search:
            conditions.extend(
                or_(
                    OPENING_BALANCES_TABLE.c.number.ilike(
                        like_pattern(token), escape="\\"
                    ),
                    OPENING_BALANCES_TABLE.c.comment.ilike(
                        like_pattern(token), escape="\\"
                    ),
                )
                for token in search.split()
            )

        total_documents = await self._session.scalar(
            select(func.count())
            .select_from(OPENING_BALANCES_TABLE)
            .where(*conditions)
        )

        stmt = (
            select(
                OPENING_BALANCES_TABLE.c.id,
                OPENING_BALANCES_TABLE.c.number,
                OPENING_BALANCES_TABLE.c.org_unit_id,
                OPENING_BALANCES_TABLE.c.status,
                OPENING_BALANCES_TABLE.c.occurred_at,
                OPENING_BALANCES_TABLE.c.posted_at,
                OPENING_BALANCES_TABLE.c.comment,
                func.count(OPENING_BALANCE_LINES_TABLE.c.id).label("line_count"),
                func.coalesce(
                    func.sum(OPENING_BALANCE_LINES_TABLE.c.total_cost), 0
                ).label("total_kopecks"),
            )
            .select_from(
                OPENING_BALANCES_TABLE.outerjoin(
                    OPENING_BALANCE_LINES_TABLE,
                    OPENING_BALANCE_LINES_TABLE.c.opening_balance_id
                    == OPENING_BALANCES_TABLE.c.id,
                )
            )
            .where(*conditions)
            .group_by(OPENING_BALANCES_TABLE.c.id)
            .order_by(
                OPENING_BALANCES_TABLE.c.occurred_at.desc(),
                OPENING_BALANCES_TABLE.c.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows], int(total_documents or 0)

    async def get(self, opening_balance_id: UUID) -> OpeningBalanceDetail | None:
        stmt = select(OPENING_BALANCES_TABLE).where(
            OPENING_BALANCES_TABLE.c.id == opening_balance_id
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(OPENING_BALANCE_LINES_TABLE)
            .where(
                OPENING_BALANCE_LINES_TABLE.c.opening_balance_id
                == opening_balance_id
            )
            .order_by(OPENING_BALANCE_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return OpeningBalanceDetail(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            comment=row["comment"],
            lines=[self._to_line(line) for line in line_rows],
            number=row["number"],
        )

    def _to_list_item(self, row: RowMapping) -> OpeningBalanceListItem:
        return OpeningBalanceListItem(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            number=row["number"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            comment=row["comment"],
            line_count=row["line_count"],
            total_kopecks=row["total_kopecks"],
        )

    def _to_line(self, row: RowMapping) -> OpeningBalanceLineItem:
        return OpeningBalanceLineItem(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            unit_cost=row["unit_cost"],
            total_kopecks=row["total_cost"],
            lot_code=row["lot_code"],
            expires_at=row["expires_at"],
        )
