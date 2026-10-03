from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee


class EmployeeRepository(ABC):
    @abstractmethod
    async def add(self, employee: Employee) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, employee: Employee) -> None:
        raise NotImplementedError
