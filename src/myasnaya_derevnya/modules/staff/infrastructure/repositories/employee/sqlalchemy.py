from uuid import UUID

from sqlalchemy import RowMapping, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.tables import EMPLOYEES_TABLE


class SQLAlchemyEmployeeRepository(EmployeeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, employee: Employee) -> None:
        stmt = insert(EMPLOYEES_TABLE).values(
            id=employee.id,
            user_id=employee.user_id,
            first_name=employee.first_name,
            last_name=employee.last_name,
            middle_name=employee.middle_name,
            phone_number=employee.phone_number.value if employee.phone_number else None,
            position=employee.position,
            hired_at=employee.hired_at,
            dismissed_at=employee.dismissed_at,
            created_at=employee.created_at,
        )
        await self._session.execute(stmt)

    async def save(self, employee: Employee) -> None:
        stmt = (
            update(EMPLOYEES_TABLE)
            .where(EMPLOYEES_TABLE.c.id == employee.id)
            .values(
                first_name=employee.first_name,
                last_name=employee.last_name,
                middle_name=employee.middle_name,
                phone_number=employee.phone_number.value
                if employee.phone_number
                else None,
                position=employee.position,
                dismissed_at=employee.dismissed_at,
            )
        )
        await self._session.execute(stmt)

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        stmt = select(EMPLOYEES_TABLE).where(EMPLOYEES_TABLE.c.id == employee_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def list(self, *, limit: int, offset: int) -> tuple[list[Employee], int]:
        total = await self._session.scalar(
            select(func.count()).select_from(EMPLOYEES_TABLE)
        )

        stmt = (
            select(EMPLOYEES_TABLE)
            .order_by(
                EMPLOYEES_TABLE.c.last_name.asc(),
                EMPLOYEES_TABLE.c.first_name.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        return [self._to_entity(row) for row in rows], total or 0

    def _to_entity(self, row: RowMapping) -> Employee:
        return Employee(
            id=row["id"],
            user_id=row["user_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            middle_name=row["middle_name"],
            phone_number=(
                PhoneNumber.parse(row["phone_number"])
                if row["phone_number"] is not None
                else None
            ),
            position=row["position"],
            hired_at=row["hired_at"],
            dismissed_at=row["dismissed_at"],
            created_at=row["created_at"],
        )
