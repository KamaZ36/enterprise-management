from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID

from myasnaya_derevnya.modules.staff.application.dto import EmployeeListItem


class EmployeeReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        org_unit_ids: Collection[UUID] | None = None,
    ) -> tuple[list[EmployeeListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        employee_id: UUID,
        org_unit_ids: Collection[UUID] | None = None,
    ) -> EmployeeListItem | None:
        raise NotImplementedError
