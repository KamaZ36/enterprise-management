from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import RowMapping, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.opening_balance import (
    OpeningBalance,
    OpeningBalanceLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.opening_balance.base import (
    OpeningBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    OPENING_BALANCE_LINES_TABLE,
    OPENING_BALANCES_TABLE,
)


class SQLAlchemyOpeningBalanceRepository(OpeningBalanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, opening_balance: OpeningBalance) -> None:
        await self._session.execute(
            insert(OPENING_BALANCES_TABLE).values(
                id=opening_balance.id,
                status=opening_balance.status.value,
                number=opening_balance.number,
                occurred_at=opening_balance.occurred_at,
                org_unit_id=opening_balance.org_unit_id,
                comment=opening_balance.comment,
                created_by=opening_balance.created_by,
                created_at=opening_balance.created_at,
                posted_at=opening_balance.posted_at,
            )
        )

        await self._insert_lines(opening_balance)

    async def save(self, opening_balance: OpeningBalance) -> None:
        await self._session.execute(
            update(OPENING_BALANCES_TABLE)
            .where(OPENING_BALANCES_TABLE.c.id == opening_balance.id)
            .values(
                status=opening_balance.status.value,
                posted_at=opening_balance.posted_at,
                occurred_at=opening_balance.occurred_at,
                comment=opening_balance.comment,
            )
        )

        await self._session.execute(
            delete(OPENING_BALANCE_LINES_TABLE).where(
                OPENING_BALANCE_LINES_TABLE.c.opening_balance_id
                == opening_balance.id
            )
        )

        await self._insert_lines(opening_balance)

    async def _insert_lines(self, opening_balance: OpeningBalance) -> None:
        lines = opening_balance.lines
        if not lines:
            return

        await self._session.execute(
            insert(OPENING_BALANCE_LINES_TABLE).values(
                [
                    {
                        "id": line.id,
                        "opening_balance_id": opening_balance.id,
                        "nomenclature_id": line.nomenclature_id,
                        "lot_id": line.lot_id,
                        "lot_code": line.lot_code,
                        "expires_at": line.expires_at,
                        "quantity": line.quantity,
                        "unit_cost": line.unit_cost,
                        "total_cost": line.total_cost.kopecks,
                    }
                    for line in lines
                ]
            )
        )

    async def attach_lot_ids(
        self, opening_balance_id: UUID, lot_ids: Mapping[UUID, UUID]
    ) -> None:
        for line_id, lot_id in lot_ids.items():
            await self._session.execute(
                update(OPENING_BALANCE_LINES_TABLE)
                .where(
                    OPENING_BALANCE_LINES_TABLE.c.id == line_id,
                    OPENING_BALANCE_LINES_TABLE.c.opening_balance_id
                    == opening_balance_id,
                )
                .values(lot_id=lot_id)
            )

    async def get_by_id(self, opening_balance_id: UUID) -> OpeningBalance | None:
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

        return self._to_entity(row, [self._to_line(line) for line in line_rows])

    async def delete(self, opening_balance_id: UUID) -> None:
        await self._session.execute(
            delete(OPENING_BALANCES_TABLE).where(
                OPENING_BALANCES_TABLE.c.id == opening_balance_id
            )
        )

    def _to_entity(
        self, row: RowMapping, lines: list[OpeningBalanceLine]
    ) -> OpeningBalance:
        return OpeningBalance(
            id=row["id"],
            status=DocumentStatus(row["status"]),
            number=row["number"],
            occurred_at=row["occurred_at"],
            org_unit_id=row["org_unit_id"],
            comment=row["comment"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            posted_at=row["posted_at"],
            lines=lines,
        )

    def _to_line(self, row: RowMapping) -> OpeningBalanceLine:
        return OpeningBalanceLine(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            unit_cost=row["unit_cost"],
            total_cost=Money(kopecks=row["total_cost"]),
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
            expires_at=row["expires_at"],
        )
