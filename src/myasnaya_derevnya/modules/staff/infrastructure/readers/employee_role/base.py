from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.staff.application.dto import EmployeeRoleListItem


class EmployeeRoleReader(ABC):
    """Чтение назначенных ролей сотрудника для интерфейса."""

    @abstractmethod
    async def list_active_for_user(self, user_id: UUID) -> list[EmployeeRoleListItem]:
        raise NotImplementedError
