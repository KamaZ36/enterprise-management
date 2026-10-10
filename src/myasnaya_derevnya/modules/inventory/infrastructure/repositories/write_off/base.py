from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.write_off import WriteOff


class WriteOffRepository(ABC):
    @abstractmethod
    async def add(self, write_off: WriteOff) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, write_off: WriteOff) -> None:
        """Сохраняет шапку. Строки после создания неизменяемы."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, write_off_id: UUID) -> WriteOff | None:
        raise NotImplementedError
