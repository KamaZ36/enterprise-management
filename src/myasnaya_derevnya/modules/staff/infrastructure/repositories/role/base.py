from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.staff.domain.entities.role import Role


class RoleRepository(ABC):
    @abstractmethod
    async def add(self, role: Role) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Role | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_code(self, code: str) -> Role | None:
        raise NotImplementedError
