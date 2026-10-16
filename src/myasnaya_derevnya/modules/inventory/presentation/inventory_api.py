from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
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
from myasnaya_derevnya.modules.inventory.application.interactors.sales.post_sale import (
    PostSaleCommand,
    PostSaleInteractor,
    SaleLineCommand,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)


@dataclass(frozen=True, slots=True)
class ReceiptLine:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class LocationInfo:
    """Складская локация (подразделение), которой оперирует inventory."""

    id: UUID
    name: str
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


@dataclass(frozen=True, slots=True)
class SaleLine:
    nomenclature_id: UUID
    quantity: Decimal


class InventoryAPI:
    def __init__(
        self,
        create_receipt_interactor: CreateReceiptInteractor,
        post_receipt_interactor: PostReceiptInteractor,
        post_production_interactor: PostProductionInteractor,
        post_sale_interactor: PostSaleInteractor,
        balance_repository: StockBalanceRepository,
        movement_repository: StockMovementRepository,
        business_api: BusinessAPI,
    ) -> None:
        self._create_receipt_interactor = create_receipt_interactor
        self._post_receipt_interactor = post_receipt_interactor
        self._post_production_interactor = post_production_interactor
        self._post_sale_interactor = post_sale_interactor
        self._balance_repository = balance_repository
        self._movement_repository = movement_repository
        self._business_api = business_api

    async def post_receipt(
        self,
        *,
        org_unit_id: UUID,
        occurred_at: datetime,
        lines: Iterable[ReceiptLine],
        supplier_name: str | None = None,
        supplier_document_number: str | None = None,
        comment: str | None = None,
    ) -> UUID:
        receipt_id = await self._create_receipt_interactor(
            CreateReceiptCommand(
                org_unit_id=org_unit_id,
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
        self, org_unit_id: UUID, nomenclature_id: UUID
    ) -> Decimal | None:
        balance = await self._balance_repository.get(org_unit_id, nomenclature_id)

        if balance is None:
            return None

        return balance.average_unit_cost

    async def has_movements(self, nomenclature_id: UUID) -> bool:
        """Есть ли по номенклатуре складские движения.

        Нужен каталогу: менять единицу измерения у номенклатуры с движениями
        нельзя.
        """
        return await self._movement_repository.count_for_nomenclature(
            nomenclature_id
        ) > 0

    async def get_location(self, org_unit_id: UUID) -> LocationInfo | None:
        location = await self._business_api.stock_location(org_unit_id)
        if location is None:
            return None

        return LocationInfo(
            id=location.id,
            name=location.name,
            is_active=location.is_active,
        )

    async def list_locations(self) -> list[LocationInfo]:
        return [
            LocationInfo(
                id=location.id,
                name=location.name,
                is_active=location.is_active,
            )
            for location in await self._business_api.stock_locations()
        ]

    async def post_production(
        self,
        *,
        document_id: UUID,
        org_unit_id: UUID,
        occurred_at: datetime,
        issues: Iterable[ProductionIssue],
        receipts: Iterable[ProductionReceipt],
        posted_by: UUID | None = None,
    ) -> PostedProduction:
        return await self._post_production_interactor(
            PostProductionCommand(
                document_id=document_id,
                org_unit_id=org_unit_id,
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

    async def post_sale(
        self,
        *,
        document_id: UUID,
        org_unit_id: UUID,
        occurred_at: datetime,
        lines: Iterable[SaleLine],
        posted_by: UUID | None = None,
    ) -> tuple[int, ...]:
        """Списывает проданные позиции и возвращает их себестоимость в копейках."""
        posted = await self._post_sale_interactor(
            PostSaleCommand(
                document_id=document_id,
                org_unit_id=org_unit_id,
                occurred_at=occurred_at,
                lines=tuple(
                    SaleLineCommand(
                        nomenclature_id=line.nomenclature_id,
                        quantity=line.quantity,
                    )
                    for line in lines
                ),
                posted_by=posted_by,
            )
        )

        return posted.line_costs_kopecks
