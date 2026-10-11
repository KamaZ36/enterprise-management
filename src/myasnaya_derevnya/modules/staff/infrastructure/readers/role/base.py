from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.staff.application.dto import RoleListItem


class RoleReader(ABC):
    @abstractmethod
    async def list(self) -> list[RoleListItem]:
        raise NotImplementedError
