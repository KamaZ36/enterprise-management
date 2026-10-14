from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.business.application.dto import (
    CafeOrgUnitListItem,
    OrgUnitListItem,
)


class OrgUnitReader(ABC):
    @abstractmethod
    async def list(self) -> list[OrgUnitListItem]:
        raise NotImplementedError

    @abstractmethod
    async def get_cafe_list(self) -> list[CafeOrgUnitListItem]:
        raise NotImplementedError
