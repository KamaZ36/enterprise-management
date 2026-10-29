from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.pos.application.dto import PosUnmappedProductItem


class PosProductMapReader(ABC):
    @abstractmethod
    async def unmapped_products(
        self, source_id: UUID, *, limit: int = 200
    ) -> list[PosUnmappedProductItem]:
        """Товары DoKa из чеков источника без действующего сопоставления."""
        raise NotImplementedError
