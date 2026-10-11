from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    WriteOffDetail,
    WriteOffListItem,
)


class WriteOffReader(ABC):
    """Чтение списаний для журнала и карточки."""

    @abstractmethod
    async def list(
        self,
        *,
        warehouse_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[WriteOffListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, write_off_id: UUID) -> WriteOffDetail | None:
        raise NotImplementedError
