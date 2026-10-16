from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.services.posting_preconditions import (
    PostingPreconditions,
)
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import EmptyDocumentError
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class SaleLineCommand:
    nomenclature_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class PostSaleCommand:
    document_id: UUID
    warehouse_id: UUID
    occurred_at: datetime
    lines: tuple[SaleLineCommand, ...]
    posted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class PostedSale:
    """Себестоимость проданных позиций в копейках, по строке на заказ."""

    line_costs_kopecks: tuple[int, ...]


class PostSaleInteractor:
    """Списывает проданный товар со склада по FEFO и считает себестоимость."""

    def __init__(
        self,
        preconditions: PostingPreconditions,
        ledger: StockLedger,
    ) -> None:
        self._preconditions = preconditions
        self._ledger = ledger

    async def __call__(self, command: PostSaleCommand) -> PostedSale:
        if not command.lines:
            raise EmptyDocumentError(command.document_id)

        await self._preconditions.ensure_ready(
            warehouse_id=command.warehouse_id,
            nomenclature_ids=[line.nomenclature_id for line in command.lines],
        )

        async with self._ledger.posting(
            document_type=DocumentType.SALE,
            document_id=command.document_id,
            warehouse_id=command.warehouse_id,
            occurred_at=command.occurred_at,
            posted_by=command.posted_by,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (command.warehouse_id, line.nomenclature_id)
                    for line in command.lines
                ],
            )

            costs: list[int] = []
            for line in command.lines:
                slices = await posting.allocate(
                    warehouse_id=command.warehouse_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                )

                line_cost = Money.zero()
                for lot_id, quantity in slices:
                    line_cost = line_cost + await posting.issue(
                        warehouse_id=command.warehouse_id,
                        nomenclature_id=line.nomenclature_id,
                        quantity=quantity,
                        movement_type=MovementType.SALE,
                        lot_id=lot_id,
                    )

                costs.append(line_cost.kopecks)

        return PostedSale(line_costs_kopecks=tuple(costs))
