from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.staff.application.dto import EmployeeListItem


class EmployeeReader(ABC):
    @abstractmethod
    async def list(
        self, *, limit: int, offset: int, search: str | None = None
    ) -> tuple[list[EmployeeListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, employee_id: UUID) -> EmployeeListItem | None:
        raise NotImplementedError
