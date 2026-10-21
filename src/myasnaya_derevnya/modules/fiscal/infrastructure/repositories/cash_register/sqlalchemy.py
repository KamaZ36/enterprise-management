from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register_binding import (
    CashRegisterBinding,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.tables import (
    CASH_REGISTER_BINDINGS_TABLE,
    CASH_REGISTERS_TABLE,
)


class SQLAlchemyCashRegisterRepository(CashRegisterRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, cash_register: CashRegister) -> None:
        await self._session.execute(
            insert(CASH_REGISTERS_TABLE).values(
                id=cash_register.id,
                reg_number=(
                    cash_register.reg_number.value
                    if cash_register.reg_number
                    else None
                ),
                serial_number=cash_register.serial_number,
                name=cash_register.name,
                fiscal_place=cash_register.fiscal_place,
                model=cash_register.model,
                fn_number=cash_register.fn_number,
                ffd_version=cash_register.ffd_version,
                company_id=cash_register.company_id,
                registered_at=cash_register.registered_at,
                deregistered_at=cash_register.deregistered_at,
                is_active=cash_register.is_active,
                attributes=cash_register.attributes,
                created_at=cash_register.created_at,
                updated_at=cash_register.updated_at,
            )
        )

    async def save(self, cash_register: CashRegister) -> None:
        await self._session.execute(
            update(CASH_REGISTERS_TABLE)
            .where(CASH_REGISTERS_TABLE.c.id == cash_register.id)
            .values(
                reg_number=(
                    cash_register.reg_number.value
                    if cash_register.reg_number
                    else None
                ),
                serial_number=cash_register.serial_number,
                name=cash_register.name,
                fiscal_place=cash_register.fiscal_place,
                model=cash_register.model,
                fn_number=cash_register.fn_number,
                ffd_version=cash_register.ffd_version,
                company_id=cash_register.company_id,
                registered_at=cash_register.registered_at,
                deregistered_at=cash_register.deregistered_at,
                is_active=cash_register.is_active,
                attributes=cash_register.attributes,
                updated_at=cash_register.updated_at,
            )
        )

    async def get_by_id(self, cash_register_id: UUID) -> CashRegister | None:
        stmt = select(CASH_REGISTERS_TABLE).where(
            CASH_REGISTERS_TABLE.c.id == cash_register_id
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return await self._to_entity(row)

    async def get_by_reg_number(self, reg_number: str) -> CashRegister | None:
        stmt = select(CASH_REGISTERS_TABLE).where(
            CASH_REGISTERS_TABLE.c.reg_number == reg_number
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return await self._to_entity(row)

    async def add_binding(self, binding: CashRegisterBinding) -> None:
        await self._session.execute(
            insert(CASH_REGISTER_BINDINGS_TABLE).values(
                id=binding.id,
                cash_register_id=binding.cash_register_id,
                org_unit_id=binding.org_unit_id,
                effective_from=binding.effective_from,
                effective_to=binding.effective_to,
                created_at=binding.created_at,
            )
        )

    async def close_binding(self, binding: CashRegisterBinding) -> None:
        await self._session.execute(
            update(CASH_REGISTER_BINDINGS_TABLE)
            .where(CASH_REGISTER_BINDINGS_TABLE.c.id == binding.id)
            .values(effective_to=binding.effective_to)
        )

    async def _to_entity(self, row: RowMapping) -> CashRegister:
        bindings = await self._load_bindings(row["id"])

        return CashRegister(
            id=row["id"],
            reg_number=(
                RegNumber.parse(row["reg_number"])
                if row["reg_number"]
                else None
            ),
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
            attributes=row["attributes"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            bindings=bindings,
        )

    async def _load_bindings(self, cash_register_id: UUID) -> list[CashRegisterBinding]:
        stmt = (
            select(CASH_REGISTER_BINDINGS_TABLE)
            .where(
                CASH_REGISTER_BINDINGS_TABLE.c.cash_register_id == cash_register_id
            )
            .order_by(CASH_REGISTER_BINDINGS_TABLE.c.effective_from.asc())
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            CashRegisterBinding(
                id=row["id"],
                cash_register_id=row["cash_register_id"],
                org_unit_id=row["org_unit_id"],
                effective_from=row["effective_from"],
                effective_to=row["effective_to"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
