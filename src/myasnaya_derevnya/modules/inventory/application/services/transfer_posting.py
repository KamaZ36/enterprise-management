from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import Transfer
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    BalanceKey,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.base import (
    LotBalanceKey,
)


class TransferPosting:
    def __init__(self, ledger: StockLedger, lot_resolver: LotResolver) -> None:
        self._ledger = ledger
        self._lot_resolver = lot_resolver

    async def post(self, *, transfer: Transfer, posted_by: UUID | None = None) -> None:
        lot_ids = await self._resolve_lots(transfer)

        async with self._ledger.posting(
            document_type=DocumentType.TRANSFER,
            document_id=transfer.id,
            warehouse_id=transfer.from_warehouse_id,
            occurred_at=transfer.occurred_at,
            posted_by=posted_by,
        ) as posting:
            await posting.lock(
                balance_keys=self._balance_keys(transfer),
                lot_keys=self._lot_keys(transfer, lot_ids),
            )

            for line, lot_id in zip(transfer.lines, lot_ids, strict=True):
                cost = await posting.issue(
                    warehouse_id=transfer.from_warehouse_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    movement_type=MovementType.TRANSFER_OUT,
                    lot_id=lot_id,
                )

                await posting.receive(
                    warehouse_id=transfer.to_warehouse_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
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

    def _lot_keys(
        self, transfer: Transfer, lot_ids: list[UUID | None]
    ) -> list[LotBalanceKey]:
        return [
            (warehouse_id, line.nomenclature_id, lot_id)
            for warehouse_id in (transfer.from_warehouse_id, transfer.to_warehouse_id)
            for line, lot_id in zip(transfer.lines, lot_ids, strict=True)
            if lot_id is not None
        ]

    async def _resolve_lots(self, transfer: Transfer) -> list[UUID | None]:
        lot_ids: list[UUID | None] = []

        for line in transfer.lines:
            if line.lot_id is not None:
                lot_ids.append(line.lot_id)
            elif line.lot_code:
                lot_ids.append(
                    await self._lot_resolver.require(
                        nomenclature_id=line.nomenclature_id,
                        lot_code=line.lot_code,
                    )
                )
            else:
                lot_ids.append(None)

        return lot_ids
