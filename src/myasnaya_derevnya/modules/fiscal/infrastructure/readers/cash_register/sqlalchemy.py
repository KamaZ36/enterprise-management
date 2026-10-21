from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import RowMapping, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.fiscal.application.dto import (
    CashRegisterBindingItem,
    CashRegisterDetail,
    CashRegisterListItem,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.base import (
    CashRegisterReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.tables import (
    CASH_REGISTER_BINDINGS_TABLE,
    CASH_REGISTERS_TABLE,
)
from myasnaya_derevnya.utils import get_datetime_utc


class SQLAlchemyCashRegisterReader(CashRegisterReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_id: UUID | None,
        at: datetime,
    ) -> list[CashRegisterListItem]:
        stmt = self._select_with_current_binding(at).order_by(
            CASH_REGISTERS_TABLE.c.name.asc()
        )

        if org_unit_id is not None:
            stmt = stmt.where(self._current_org_unit_id(at) == org_unit_id)

        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows]

    async def get(self, cash_register_id: UUID) -> CashRegisterDetail | None:
        at = get_datetime_utc()
        stmt = self._select_with_current_binding(at).where(
            CASH_REGISTERS_TABLE.c.id == cash_register_id
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        bindings_stmt = (
            select(CASH_REGISTER_BINDINGS_TABLE)
            .where(
                CASH_REGISTER_BINDINGS_TABLE.c.cash_register_id == cash_register_id
            )
            .order_by(CASH_REGISTER_BINDINGS_TABLE.c.effective_from.desc())
        )
        binding_rows = (await self._session.execute(bindings_stmt)).mappings().all()

        item = self._to_list_item(row)

        return CashRegisterDetail(
            **asdict(item),
            bindings=tuple(
                CashRegisterBindingItem(
                    id=binding["id"],
                    org_unit_id=binding["org_unit_id"],
                    effective_from=binding["effective_from"],
                    effective_to=binding["effective_to"],
                )
                for binding in binding_rows
            ),
        )

    def _select_with_current_binding(self, at: datetime):
        return select(
            CASH_REGISTERS_TABLE,
            self._current_org_unit_id(at).label("org_unit_id"),
        )

    def _current_org_unit_id(self, at: datetime):
        return (
            select(CASH_REGISTER_BINDINGS_TABLE.c.org_unit_id)
            .where(
                CASH_REGISTER_BINDINGS_TABLE.c.cash_register_id
                == CASH_REGISTERS_TABLE.c.id,
                CASH_REGISTER_BINDINGS_TABLE.c.effective_from <= at,
                or_(
                    CASH_REGISTER_BINDINGS_TABLE.c.effective_to.is_(None),
                    CASH_REGISTER_BINDINGS_TABLE.c.effective_to > at,
                ),
            )
            .order_by(CASH_REGISTER_BINDINGS_TABLE.c.effective_from.desc())
            .limit(1)
            .scalar_subquery()
        )

    def _to_list_item(self, row: RowMapping) -> CashRegisterListItem:
        return CashRegisterListItem(
            id=row["id"],
            reg_number=row["reg_number"],
            serial_number=row["serial_number"],
            name=row["name"],
            fiscal_place=row["fiscal_place"],
            model=row["model"],
            fn_number=row["fn_number"],
            ffd_version=row["ffd_version"],
            company_id=row["company_id"],
            registered_at=row["registered_at"],
            deregistered_at=row["deregistered_at"],
            is_active=row["is_active"],
            org_unit_id=row["org_unit_id"],
        )
