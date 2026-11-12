from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)


@dataclass(frozen=True, slots=True)
class UnpostProductionCommand:
    document_id: UUID


class UnpostProductionInteractor:
    """Сторнирует движения производственного задания."""

    def __init__(self, ledger: StockLedger) -> None:
        self._ledger = ledger

    async def __call__(self, command: UnpostProductionCommand) -> None:
        await self._ledger.unpost(
            document_type=DocumentType.PRODUCTION,
            document_id=command.document_id,
        )
