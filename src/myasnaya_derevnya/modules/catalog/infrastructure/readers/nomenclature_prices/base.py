from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.application.dto import NomenclaturePriceItem


class NomenclaturePricesReader(ABC):
    @abstractmethod
    async def list_by_nomenclature(
        self, nomenclature_id: UUID
    ) -> list[NomenclaturePriceItem]:
        raise NotImplementedError
