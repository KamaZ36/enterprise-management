from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.interactors.production.post_production import (
    PostedProduction,
    PostProductionCommand,
    PostProductionInteractor,
    ProductionIssueCommand,
    ProductionReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    CreateReceiptInteractor,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.warehouse.base import (
    WarehouseReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)


@dataclass(frozen=True, slots=True)
class ReceiptLine:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class WarehouseInfo:
    id: UUID
    code: str
    name: str
    type: str
    org_unit_id: UUID
    is_active: bool


@dataclass(frozen=True, slots=True)
class ProductionIssue:
    nomenclature_id: UUID
    quantity: Decimal
    lot_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProductionReceipt:
    nomenclature_id: UUID
    quantity: Decimal
    share: Decimal
    lot_code: str | None = None
    expires_at: date | None = None


class InventoryAPI:
    def __init__(
        self,
        create_receipt_interactor: CreateReceiptInteractor,
        post_receipt_interactor: PostReceiptInteractor,
        post_production_interactor: PostProductionInteractor,
        balance_repository: StockBalanceRepository,
        warehouse_repository: WarehouseRepository,
        warehouse_reader: WarehouseReader,
    ) -> None:
        self._create_receipt_interactor = create_receipt_interactor
        self._post_receipt_interactor = post_receipt_interactor
        self._post_production_interactor = post_production_interactor
        self._balance_repository = balance_repository
        self._warehouse_repository = warehouse_repository
        self._warehouse_reader = warehouse_reader

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

    async def get_warehouse(self, warehouse_id: UUID) -> WarehouseInfo | None:
        warehouse = await self._warehouse_repository.get_by_id(warehouse_id)
        if warehouse is None:
            return None

        return WarehouseInfo(
            id=warehouse.id,
            code=warehouse.code,
            name=warehouse.name,
            type=warehouse.type.value,
            org_unit_id=warehouse.org_unit_id,
            is_active=warehouse.is_active,
        )

    async def list_warehouses(self) -> list[WarehouseInfo]:
        return [
            WarehouseInfo(
                id=warehouse.id,
                code=warehouse.code,
                name=warehouse.name,
                type=warehouse.type.value,
                org_unit_id=warehouse.org_unit_id,
                is_active=warehouse.is_active,
            )
            for warehouse in await self._warehouse_reader.list_all()
        ]

    async def post_production(
        self,
        *,
        document_id: UUID,
        warehouse_id: UUID,
        occurred_at: datetime,
        issues: Iterable[ProductionIssue],
        receipts: Iterable[ProductionReceipt],
        posted_by: UUID | None = None,
    ) -> PostedProduction:
        return await self._post_production_interactor(
            PostProductionCommand(
                document_id=document_id,
                warehouse_id=warehouse_id,
                occurred_at=occurred_at,
                issues=tuple(
                    ProductionIssueCommand(
                        nomenclature_id=issue.nomenclature_id,
                        quantity=issue.quantity,
                        lot_id=issue.lot_id,
                    )
                    for issue in issues
                ),
                receipts=tuple(
                    ProductionReceiptCommand(
                        nomenclature_id=receipt.nomenclature_id,
                        quantity=receipt.quantity,
                        share=receipt.share,
                        lot_code=receipt.lot_code,
                        produced_at=occurred_at.date(),
                        expires_at=receipt.expires_at,
                    )
                    for receipt in receipts
                ),
                posted_by=posted_by,
            )
        )
