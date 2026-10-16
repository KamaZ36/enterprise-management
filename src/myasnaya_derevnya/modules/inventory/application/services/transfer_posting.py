from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
    StockPostingHandle,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    BalanceKey,
)


class TransferPosting:
    def __init__(self, ledger: StockLedger, lot_resolver: LotResolver) -> None:
        self._ledger = ledger
        self._lot_resolver = lot_resolver

    async def post(self, *, transfer: Transfer, posted_by: UUID | None = None) -> None:
        async with self._ledger.posting(
            document_type=DocumentType.TRANSFER,
            document_id=transfer.id,
            warehouse_id=transfer.from_warehouse_id,
            occurred_at=transfer.occurred_at,
            posted_by=posted_by,
        ) as posting:
            await posting.lock(balance_keys=self._balance_keys(transfer))

            for line in transfer.lines:
                slices = await self._source_slices(
                    posting, transfer.from_warehouse_id, line
                )

                for lot_id, quantity in slices:
                    cost = await posting.issue(
                        warehouse_id=transfer.from_warehouse_id,
                        nomenclature_id=line.nomenclature_id,
                        quantity=quantity,
                        movement_type=MovementType.TRANSFER_OUT,
                        lot_id=lot_id,
                    )

                    if lot_id is not None:
                        await posting.lock(
                            lot_keys=[
                                (
                                    transfer.to_warehouse_id,
                                    line.nomenclature_id,
                                    lot_id,
                                )
                            ]
                        )

                    await posting.receive(
                        warehouse_id=transfer.to_warehouse_id,
                        nomenclature_id=line.nomenclature_id,
                        quantity=quantity,
                        cost=cost,
                        movement_type=MovementType.TRANSFER_IN,
                        lot_id=lot_id,
                    )

    def _balance_keys(self, transfer: Transfer) -> list[BalanceKey]:
        return [
            (warehouse_id, line.nomenclature_id)
            for warehouse_id in (transfer.from_warehouse_id, transfer.to_warehouse_id)
            for line in transfer.lines
        ]

    async def _source_slices(
        self,
        posting: StockPostingHandle,
        warehouse_id: UUID,
        line: TransferLine,
    ) -> list[tuple[UUID | None, Decimal]]:
        if line.lot_id is not None:
            await posting.lock(
                lot_keys=[(warehouse_id, line.nomenclature_id, line.lot_id)]
            )
            return [(line.lot_id, line.quantity)]

        if line.lot_code:
            lot_id = await self._lot_resolver.require(
                nomenclature_id=line.nomenclature_id,
                lot_code=line.lot_code,
            )
            await posting.lock(
                lot_keys=[(warehouse_id, line.nomenclature_id, lot_id)]
            )
            return [(lot_id, line.quantity)]

        return await posting.allocate(
            warehouse_id=warehouse_id,
            nomenclature_id=line.nomenclature_id,
            quantity=line.quantity,
        )
