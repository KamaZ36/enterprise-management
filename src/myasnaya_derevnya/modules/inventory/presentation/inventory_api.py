from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.commands import ReceiptLineCommand
from myasnaya_derevnya.modules.inventory.application.interactors.create_receipt import (
    CreateReceiptCommand,
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_receipt import (
    PostReceiptCommand,
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)


@dataclass(frozen=True, slots=True)
class ReceiptLine:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    lot_code: str | None = None
    expires_at: date | None = None


class InventoryAPI:
    """Публичный интерфейс складского модуля для других модулей."""

    def __init__(
        self,
        create_receipt_interactor: CreateReceiptInteractor,
        post_receipt_interactor: PostReceiptInteractor,
        balance_repository: StockBalanceRepository,
    ) -> None:
        self._create_receipt_interactor = create_receipt_interactor
        self._post_receipt_interactor = post_receipt_interactor
        self._balance_repository = balance_repository

    async def post_receipt(
        self,
        *,
        warehouse_id: UUID,
        occurred_at: datetime,
        lines: Iterable[ReceiptLine],
        supplier_name: str | None = None,
        supplier_document_number: str | None = None,
        comment: str | None = None,
    ) -> UUID:
        """Создаёт и сразу проводит поступление. Возвращает id поступления."""
        receipt_id = await self._create_receipt_interactor(
            CreateReceiptCommand(
                warehouse_id=warehouse_id,
                occurred_at=occurred_at,
                supplier_name=supplier_name,
                supplier_document_number=supplier_document_number,
                comment=comment,
                lines=[
                    ReceiptLineCommand(
                        nomenclature_id=line.nomenclature_id,
                        quantity=line.quantity,
                        unit_cost=line.unit_cost,
                        lot_code=line.lot_code,
                        expires_at=line.expires_at,
                    )
                    for line in lines
                ],
            )
        )

        await self._post_receipt_interactor(PostReceiptCommand(receipt_id=receipt_id))

        return receipt_id

    async def average_unit_cost(
        self, warehouse_id: UUID, nomenclature_id: UUID
    ) -> Decimal | None:
        balance = await self._balance_repository.get(warehouse_id, nomenclature_id)

        if balance is None:
            return None

        return balance.average_unit_cost
