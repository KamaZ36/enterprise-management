from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_product_alias import (
    OfdProductAlias,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdReceipt,
    OfdReceiptLine,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_sync_run import OfdSyncRun


class OfdReceiptRepository(ABC):
    @abstractmethod
    async def add_if_absent(self, receipt: OfdReceipt) -> bool:
        """Сохраняет чек, если такого фискального документа ещё нет."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, receipt_id: UUID) -> OfdReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_line_id(self, line_id: UUID) -> OfdReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, receipt: OfdReceipt) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_line(self, line: OfdReceiptLine) -> None:
        raise NotImplementedError

    @abstractmethod
    async def ready_receipt_ids(self, *, limit: int) -> list[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def needs_location_receipts(
        self, reg_number: str, *, limit: int = 100
    ) -> list[OfdReceipt]:
        """Чеки кассы, которым ещё не определён склад."""
        raise NotImplementedError

    @abstractmethod
    async def add_sync_run(self, run: OfdSyncRun) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_sync_run(self, run: OfdSyncRun) -> None:
        raise NotImplementedError

    @abstractmethod
    async def alias_by_barcode(self, barcode: str) -> OfdProductAlias | None:
        raise NotImplementedError

    @abstractmethod
    async def save_alias(self, alias: OfdProductAlias) -> None:
        raise NotImplementedError
