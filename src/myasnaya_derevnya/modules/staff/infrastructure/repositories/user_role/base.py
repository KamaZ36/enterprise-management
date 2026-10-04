from abc import ABC
from uuid import UUID

from myasnaya_derevnya.modules.staff.domain.entities.user_role import UserRole


class UserRoleRepository(ABC):
    async def add(self, user_role: UserRole) -> None:
        raise NotImplementedError

    async def get_by_user_id(self, user_id: UUID) -> UserRole | None:
        raise NotImplementedError
