from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.infrastructure.employee.base import (
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
            phone=employee.phone_number.value if employee.phone_number else None,
            position=employee.position,
            hired_at=employee.hired_at,
            dismissed_at=employee.dismissed_at,
            created_at=employee.created_at,
        )
        await self._session.execute(stmt)
