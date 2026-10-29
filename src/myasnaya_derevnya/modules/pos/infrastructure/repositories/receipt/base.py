from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.pos.domain.entities.receipt import PosReceipt


class PosReceiptRepository(ABC):
    @abstractmethod
    async def add_if_absent(self, receipt: PosReceipt) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, receipt_id: UUID) -> PosReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_source_guid(
        self, source_id: UUID, external_guid: str
    ) -> PosReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, receipt: PosReceipt) -> None:
        raise NotImplementedError

    @abstractmethod
    async def apply_mapping(
        self,
        *,
        source_id: UUID,
        doka_product_guid: str,
        nomenclature_id: UUID,
        unit_factor,
    ) -> list[UUID]:
        """Проставляет номенклатуру в ещё не проведённых чеках источника."""
        raise NotImplementedError

    @abstractmethod
    async def pending_receipt_ids(
        self, *, statuses: Iterable[str], limit: int
    ) -> list[UUID]:
        raise NotImplementedError
