from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.staff.domain.entities.role import Role


class RoleRepository(ABC):
    @abstractmethod
    async def add(self, role: Role) -> None:
        raise NotImplementedError
