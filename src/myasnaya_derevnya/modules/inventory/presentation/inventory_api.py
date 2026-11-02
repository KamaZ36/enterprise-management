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
from myasnaya_derevnya.modules.inventory.domain.errors import (
    StockLotNotFoundByIdError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.lot_balance.base import (
    LotBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.base import (
    StockLotRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.base import (
    StockPostingRepository,
)


@dataclass(frozen=True, slots=True)
class ReceiptLine:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    lot_code: str | None = None
    expires_at: date | None = None
    vetis_vsd_number: str | None = None
    vetis_vsd_guid: UUID | None = None
    vetis_batch_id: str | None = None
    vetis_product_item_guid: UUID | None = None


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
    vetis_vsd_number: str | None = None
    vetis_vsd_guid: UUID | None = None
    vetis_batch_id: str | None = None


@dataclass(frozen=True, slots=True)
class SaleLine:
    nomenclature_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class LotOption:
    """Доступная партия для выбора в другом модуле."""

    id: UUID
    nomenclature_id: UUID
    code: str
    quantity: Decimal
    expires_at: date | None = None


class InventoryAPI:
    def __init__(
        self,
        create_receipt_interactor: CreateReceiptInteractor,
        post_receipt_interactor: PostReceiptInteractor,
        post_production_interactor: PostProductionInteractor,
        post_sale_interactor: PostSaleInteractor,
        balance_repository: StockBalanceRepository,
        movement_repository: StockMovementRepository,
        posting_repository: StockPostingRepository,
        lot_repository: StockLotRepository,
        lot_balance_reader: LotBalanceReader,
        business_api: BusinessAPI,
    ) -> None:
        self._create_receipt_interactor = create_receipt_interactor
        self._post_receipt_interactor = post_receipt_interactor
        self._post_production_interactor = post_production_interactor
        self._post_sale_interactor = post_sale_interactor
        self._balance_repository = balance_repository
        self._movement_repository = movement_repository
        self._posting_repository = posting_repository
        self._lot_repository = lot_repository
        self._lot_balance_reader = lot_balance_reader
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
                        vetis_vsd_number=line.vetis_vsd_number,
                        vetis_vsd_guid=line.vetis_vsd_guid,
                        vetis_batch_id=line.vetis_batch_id,
                        vetis_product_item_guid=line.vetis_product_item_guid,
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

    async def sale_posting_exists(self, document_id: UUID) -> bool:
        """Проведена ли продажа с таким идентификатором документа."""

        return await self._posting_repository.exists(
            document_type=DocumentType.SALE.value,
            document_id=document_id,
        )

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

    async def available_lots(
        self,
        *,
        org_unit_id: UUID,
        nomenclature_ids: Iterable[UUID],
    ) -> tuple[LotOption, ...]:
        """Партии с положительным остатком по перечисленным номенклатурам."""
        unique_ids = list(dict.fromkeys(nomenclature_ids))
        if not unique_ids:
            return ()

        items, _ = await self._lot_balance_reader.list_by_org_unit(
            org_unit_id,
            with_cost=False,
            nomenclature_ids=unique_ids,
            limit=500,
            offset=0,
        )

        return tuple(
            LotOption(
                id=item.lot_id,
                nomenclature_id=item.nomenclature_id,
                code=item.lot_code,
                quantity=item.quantity,
                expires_at=item.expires_at,
            )
            for item in items
        )

    async def lot_codes(self, lot_ids: Iterable[UUID]) -> dict[UUID, str]:
        """Коды партий по идентификаторам (включая уже израсходованные)."""
        result: dict[UUID, str] = {}

        for lot_id in dict.fromkeys(lot_ids):
            lot = await self._lot_repository.get_by_id(lot_id)
            if lot is not None:
                result[lot_id] = lot.lot_code

        return result

    async def set_lot_vetis(
        self,
        *,
        lot_id: UUID,
        vsd_number: str | None = None,
        vsd_guid: UUID | None = None,
        batch_id: str | None = None,
        product_item_guid: UUID | None = None,
        entered_by: UUID | None = None,
    ) -> None:
        """Привязывает ВСД к уже существующей партии."""
        lot = await self._lot_repository.get_by_id(lot_id)
        if lot is None:
            raise StockLotNotFoundByIdError(lot_id)

        lot.attach_vetis(
            vsd_number=vsd_number,
            vsd_guid=vsd_guid,
            batch_id=batch_id,
            product_item_guid=product_item_guid,
            entered_by=entered_by,
        )
        await self._lot_repository.save(lot)

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
                        vetis_vsd_number=receipt.vetis_vsd_number,
                        vetis_vsd_guid=receipt.vetis_vsd_guid,
                        vetis_batch_id=receipt.vetis_batch_id,
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
