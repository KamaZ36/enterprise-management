from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.services.cost_split import (
    split_kopecks,
)
from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
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
class ProductionIssueCommand:
    nomenclature_id: UUID
    quantity: Decimal
    lot_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProductionReceiptCommand:
    nomenclature_id: UUID
    quantity: Decimal
    share: Decimal
    lot_code: str | None = None
    produced_at: date | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class PostProductionCommand:
    document_id: UUID
    warehouse_id: UUID
    occurred_at: datetime
    issues: tuple[ProductionIssueCommand, ...]
    receipts: tuple[ProductionReceiptCommand, ...]
    posted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class PostedProductionReceipt:
    nomenclature_id: UUID
    quantity: Decimal
    cost_kopecks: int
    lot_id: UUID | None


@dataclass(frozen=True, slots=True)
class PostedProduction:
    issued_cost_kopecks: int
    receipts: tuple[PostedProductionReceipt, ...]


class PostProductionInteractor:
    def __init__(
        self,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
    ) -> None:
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger

    async def __call__(self, command: PostProductionCommand) -> PostedProduction:
        if not command.issues or not command.receipts:
            raise EmptyDocumentError(command.document_id)

        warehouse_id = command.warehouse_id

        await self._preconditions.ensure_ready(
            warehouse_id=warehouse_id,
            nomenclature_ids=[
                *(issue.nomenclature_id for issue in command.issues),
                *(receipt.nomenclature_id for receipt in command.receipts),
            ],
        )

        issue_lots = [issue.lot_id for issue in command.issues]
        receipt_lots = [
            await self._lot_resolver.find_or_create(
                nomenclature_id=receipt.nomenclature_id,
                lot_code=receipt.lot_code,
                produced_at=receipt.produced_at,
                expires_at=receipt.expires_at,
            )
            for receipt in command.receipts
        ]

        async with self._ledger.posting(
            document_type=DocumentType.PRODUCTION,
            document_id=command.document_id,
            warehouse_id=warehouse_id,
            occurred_at=command.occurred_at,
            posted_by=command.posted_by,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    *(
                        (warehouse_id, issue.nomenclature_id)
                        for issue in command.issues
                    ),
                    *(
                        (warehouse_id, receipt.nomenclature_id)
                        for receipt in command.receipts
                    ),
                ],
                lot_keys=[
                    *(
                        (warehouse_id, issue.nomenclature_id, lot_id)
                        for issue, lot_id in zip(
                            command.issues, issue_lots, strict=True
                        )
                        if lot_id is not None
                    ),
                    *(
                        (warehouse_id, receipt.nomenclature_id, lot_id)
                        for receipt, lot_id in zip(
                            command.receipts, receipt_lots, strict=True
                        )
                        if lot_id is not None
                    ),
                ],
            )

            issued = Money.zero()
            for issue, lot_id in zip(command.issues, issue_lots, strict=True):
                issued = issued + await posting.issue(
                    warehouse_id=warehouse_id,
                    nomenclature_id=issue.nomenclature_id,
                    quantity=issue.quantity,
                    movement_type=MovementType.PRODUCTION_OUT,
                    lot_id=lot_id,
                )

            costs = split_kopecks(
                issued.kopecks, [receipt.share for receipt in command.receipts]
            )

            posted: list[PostedProductionReceipt] = []
            for receipt, lot_id, cost in zip(
                command.receipts, receipt_lots, costs, strict=True
            ):
                await posting.receive(
                    warehouse_id=warehouse_id,
                    nomenclature_id=receipt.nomenclature_id,
                    quantity=receipt.quantity,
                    cost=Money(kopecks=cost),
                    movement_type=MovementType.PRODUCTION_IN,
                    lot_id=lot_id,
                )
                posted.append(
                    PostedProductionReceipt(
                        nomenclature_id=receipt.nomenclature_id,
                        quantity=receipt.quantity,
                        cost_kopecks=cost,
                        lot_id=lot_id,
                    )
                )

        return PostedProduction(
            issued_cost_kopecks=issued.kopecks,
            receipts=tuple(posted),
        )
