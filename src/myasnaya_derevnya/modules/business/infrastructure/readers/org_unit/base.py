from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem


class OrgUnitReader(ABC):
    @abstractmethod
    async def list(self) -> list[OrgUnitListItem]:
        raise NotImplementedError
