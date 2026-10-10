from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem


class OrgUnitReader(ABC):
    """Чтение оргструктуры для интерфейса: плоские DTO вместо доменных сущностей."""

    @abstractmethod
    async def list(self) -> list[OrgUnitListItem]:
        raise NotImplementedError
