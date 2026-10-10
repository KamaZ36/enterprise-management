from abc import ABC, abstractmethod
from collections.abc import Sequence

from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    StockMovement,
)


class StockMovementRepository(ABC):
    """Журнал проводок: только запись и чтение, без изменения и удаления."""

    @abstractmethod
    async def add_many(self, movements: Sequence[StockMovement]) -> None:
        raise NotImplementedError
