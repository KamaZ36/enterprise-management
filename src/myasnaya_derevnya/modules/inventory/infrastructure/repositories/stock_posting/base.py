from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.inventory.domain.entities.stock_posting import (
    StockPosting,
)


class StockPostingRepository(ABC):
    @abstractmethod
    async def add(self, posting: StockPosting) -> None:
        raise NotImplementedError
