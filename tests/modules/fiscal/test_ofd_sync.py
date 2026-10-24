from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest

from myasnaya_derevnya.core.settings.ofd import OfdSettings
from myasnaya_derevnya.modules.fiscal.application.errors import (
    InvalidOfdPeriodError,
    OfdApiError,
    OfdPeriodBeforeCutoverError,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.map_ofd_receipt_line import (
    MapOfdReceiptLineCommand,
    MapOfdReceiptLineInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ofd_receipt import (
    PostOfdReceiptCommand,
    PostOfdReceiptInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.services.ofd_sync import (
    OfdSyncService,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_product_alias import (
    OfdProductAlias,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdLineMappingStatus,
    OfdReceipt,
    OfdReceiptLine,
    OfdReceiptStatus,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_sync_run import (
    OfdSyncRun,
    OfdSyncRunStatus,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.ofd.client import (
    OfdClient,
    OfdReceiptItemPayload,
    OfdReceiptPayload,
)
from myasnaya_derevnya.modules.inventory.domain.errors import InsufficientStockError
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import SaleLine
from tests.modules.fiscal.fakes import (
    FakeIdentityProvider,
    FakeStaffAPI,
    FakeTransactionManager,
)

ORG_UNIT_ID = uuid4()
NOMENCLATURE_ID = uuid4()
REG_NUMBER = "0000000000051264"


def settings(*, cutover_date: date | None = None) -> OfdSettings:
    return OfdSettings(
        ofd_api_url="https://example.test/api/integration/v2",
        ofd_api_token="token",
        ofd_inn="2308139496",
        ofd_timezone="Europe/Moscow",
        ofd_cutover_date=cutover_date,
    )


def payload(
    *,
    doc_number: int = 10,
    operation_type: str = "Income",
    is_correction: bool = False,
    barcode: str | None = "0123456789012",
    quantity: Decimal = Decimal(1),
) -> OfdReceiptPayload:
    item = OfdReceiptItemPayload(
        name="Кофе",
        price_kopecks=13000,
        quantity=quantity,
        total_kopecks=13000,
        barcode=barcode,
        product_code={},
        unit="0",
        raw={"Name": "Кофе", "Barcode": barcode},
    )
    return OfdReceiptPayload(
        raw_id=f"raw-{doc_number}",
        c_date_utc=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        doc_datetime_local=datetime(2026, 10, 24, 12, 0),
        operation_type=operation_type,
        is_bso=False,
        is_correction=is_correction,
        user_inn="2308139496",
        kkt_reg_number=REG_NUMBER,
        fn_number="9999078902009926",
        doc_number=doc_number,
        fiscal_sign=str(1000 + doc_number),
        total_kopecks=13000,
        cash_kopecks=13000,
        ecash_kopecks=0,
        items=(item,),
        raw={"DocNumber": doc_number},
    )


class FakeOfdClient:
    def __init__(self, receipts: list[OfdReceiptPayload]) -> None:
        self.receipts = receipts
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch_receipts(
        self, *, reg_number: str, date_from: datetime, date_to: datetime
    ) -> list[OfdReceiptPayload]:
        self.calls.append((reg_number, date_from, date_to))
        return self.receipts


class FakeFiscalAPI:
    def __init__(self, org_unit_id: UUID | None = ORG_UNIT_ID) -> None:
        self.org_unit_id = org_unit_id
        self.register_found = True

    async def cash_register_by_reg_number(self, reg_number: str):
        if not self.register_found:
            return None
        return type(
            "CashRegisterInfo",
            (),
            {"id": uuid4(), "reg_number": reg_number, "name": "Касса"},
        )()

    async def cash_register_location_at(self, reg_number: str, at: datetime):
        return self.org_unit_id


class FakeCatalogAPI:
    def __init__(self, by_gtin: dict[str, UUID] | None = None) -> None:
        self.by_gtin = by_gtin or {}
        self.names = {NOMENCLATURE_ID: "Кофе"}

    async def nomenclature_id_by_gtin(self, gtin: str) -> UUID | None:
        return self.by_gtin.get(gtin)

    async def nomenclature_names(self, ids):
        return {item: self.names[item] for item in ids if item in self.names}


class FakeOfdReceiptRepository:
    def __init__(self) -> None:
        self.receipts: dict[UUID, OfdReceipt] = {}
        self.by_identity: dict[tuple, UUID] = {}
        self.aliases: dict[str, OfdProductAlias] = {}
        self.sync_runs: dict[UUID, OfdSyncRun] = {}

    async def add_if_absent(self, receipt: OfdReceipt) -> bool:
        key = (
            receipt.reg_number,
            receipt.fn_number,
            receipt.doc_number,
            receipt.fiscal_sign,
        )
        if key in self.by_identity:
            return False
        self.by_identity[key] = receipt.id
        self.receipts[receipt.id] = receipt
        return True

    async def get_by_id(self, receipt_id: UUID) -> OfdReceipt | None:
        return self.receipts.get(receipt_id)

    async def get_by_line_id(self, line_id: UUID) -> OfdReceipt | None:
        for receipt in self.receipts.values():
            if any(line.id == line_id for line in receipt.lines):
                return receipt
        return None

    async def save(self, receipt: OfdReceipt) -> None:
        self.receipts[receipt.id] = receipt

    async def save_line(self, line: OfdReceiptLine) -> None:
        return None

    async def ready_receipt_ids(self, *, limit: int) -> list[UUID]:
        return [
            receipt.id
            for receipt in self.receipts.values()
            if receipt.status is OfdReceiptStatus.READY
        ][:limit]

    async def needs_location_receipts(
        self, reg_number: str, *, limit: int = 100
    ) -> list[OfdReceipt]:
        return [
            receipt
            for receipt in self.receipts.values()
            if receipt.reg_number == reg_number
            and receipt.status is OfdReceiptStatus.NEEDS_LOCATION
        ][:limit]

    async def add_sync_run(self, run: OfdSyncRun) -> None:
        self.sync_runs[run.id] = run

    async def save_sync_run(self, run: OfdSyncRun) -> None:
        self.sync_runs[run.id] = run

    async def alias_by_barcode(self, barcode: str) -> OfdProductAlias | None:
        return self.aliases.get(barcode)

    async def save_alias(self, alias: OfdProductAlias) -> None:
        self.aliases[alias.barcode] = alias


class FakeInventoryAPI:
    def __init__(self) -> None:
        self.posted: set[UUID] = set()
        self.calls: list[tuple[UUID, UUID, tuple[SaleLine, ...]]] = []
        self.fail: Exception | None = None

    async def sale_posting_exists(self, document_id: UUID) -> bool:
        return document_id in self.posted

    async def post_sale(
        self,
        *,
        document_id: UUID,
        org_unit_id: UUID,
        occurred_at: datetime,
        lines,
        posted_by: UUID | None = None,
    ):
        if self.fail is not None:
            raise self.fail
        self.posted.add(document_id)
        self.calls.append((document_id, org_unit_id, tuple(lines)))
        return ()


def build_sync_service(
    *,
    client: FakeOfdClient,
    repository: FakeOfdReceiptRepository,
    fiscal_api: FakeFiscalAPI | None = None,
    catalog_api: FakeCatalogAPI | None = None,
    transaction_manager: FakeTransactionManager | None = None,
    ofd_settings: OfdSettings | None = None,
) -> OfdSyncService:
    return OfdSyncService(
        ofd_client=client,
        settings=ofd_settings or settings(),
        fiscal_api=fiscal_api or FakeFiscalAPI(),
        catalog_api=catalog_api or FakeCatalogAPI(),
        receipt_repository=repository,
        transaction_manager=transaction_manager or FakeTransactionManager(),
    )


async def test_sync_stores_receipt_and_maps_barcode() -> None:
    repository = FakeOfdReceiptRepository()
    catalog = FakeCatalogAPI(by_gtin={"0123456789012": NOMENCLATURE_ID})
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
        catalog_api=catalog,
    )

    result = await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    assert result.status == OfdSyncRunStatus.SUCCESS.value
    assert result.receipts_found == 1
    assert result.receipts_created == 1

    receipt = next(iter(repository.receipts.values()))
    assert receipt.status is OfdReceiptStatus.READY
    assert receipt.org_unit_id == ORG_UNIT_ID
    assert receipt.doc_datetime == datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
    assert receipt.lines[0].mapping_status is OfdLineMappingStatus.MAPPED
    assert receipt.lines[0].nomenclature_id == NOMENCLATURE_ID


async def test_sync_without_binding_waits_for_location() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
        fiscal_api=FakeFiscalAPI(org_unit_id=None),
    )

    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    receipt = next(iter(repository.receipts.values()))
    assert receipt.status is OfdReceiptStatus.NEEDS_LOCATION


async def test_sync_ignores_refund_and_correction() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient(
            [payload(doc_number=11, operation_type="Refund income")]
        ),
        repository=repository,
    )

    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    receipt = next(iter(repository.receipts.values()))
    assert receipt.status is OfdReceiptStatus.IGNORED


async def test_sync_is_idempotent_by_fiscal_identity() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
    )

    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )
    result = await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    assert result.receipts_found == 1
    assert result.receipts_created == 0
    assert len(repository.receipts) == 1


async def test_map_line_saves_alias_and_makes_receipt_ready() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
    )
    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )
    receipt = next(iter(repository.receipts.values()))
    line = receipt.lines[0]

    interactor = MapOfdReceiptLineInteractor(
        identity_provider=FakeIdentityProvider(),
        staff_api=FakeStaffAPI(),
        catalog_api=FakeCatalogAPI(),
        receipt_repository=repository,
        transaction_manager=FakeTransactionManager(),
    )

    result = await interactor(
        MapOfdReceiptLineCommand(
            line_id=line.id,
            nomenclature_id=NOMENCLATURE_ID,
            remember_barcode=True,
        )
    )

    assert result.receipt_status == OfdReceiptStatus.READY.value
    assert line.nomenclature_id == NOMENCLATURE_ID
    assert repository.aliases["0123456789012"].nomenclature_id == NOMENCLATURE_ID


async def test_post_receipt_calls_inventory_and_marks_posted() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
        catalog_api=FakeCatalogAPI(by_gtin={"0123456789012": NOMENCLATURE_ID}),
    )
    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )
    receipt = next(iter(repository.receipts.values()))
    inventory = FakeInventoryAPI()

    interactor = PostOfdReceiptInteractor(
        identity_provider=FakeIdentityProvider(),
        staff_api=FakeStaffAPI(),
        receipt_repository=repository,
        inventory_api=inventory,
        transaction_manager=FakeTransactionManager(),
    )

    result = await interactor(PostOfdReceiptCommand(receipt_id=receipt.id))

    assert result.status == OfdReceiptStatus.POSTED.value
    assert receipt.status is OfdReceiptStatus.POSTED
    assert inventory.calls[0][0] == receipt.id
    assert inventory.calls[0][2][0].nomenclature_id == NOMENCLATURE_ID


async def test_post_receipt_marks_failed_on_shortage() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
        catalog_api=FakeCatalogAPI(by_gtin={"0123456789012": NOMENCLATURE_ID}),
    )
    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )
    receipt = next(iter(repository.receipts.values()))
    inventory = FakeInventoryAPI()
    inventory.fail = InsufficientStockError(
        org_unit_id=ORG_UNIT_ID,
        nomenclature_id=NOMENCLATURE_ID,
        available=Decimal(0),
        requested=Decimal(1),
    )

    interactor = PostOfdReceiptInteractor(
        identity_provider=FakeIdentityProvider(),
        staff_api=FakeStaffAPI(),
        receipt_repository=repository,
        inventory_api=inventory,
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(InsufficientStockError):
        await interactor(PostOfdReceiptCommand(receipt_id=receipt.id))

    assert receipt.status is OfdReceiptStatus.FAILED
    assert "Недостаточно остатка" in (receipt.error or "")


async def test_client_parses_receipts_with_fpd_short() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(
            f"/inn/2308139496/kkt/{REG_NUMBER}/receipts-with-fpd-short"
        )
        return httpx.Response(
            200,
            json={
                "Status": "Success",
                "Data": [
                    {
                        "Id": "raw-1",
                        "CDateUtc": "2026-10-24T09:00:00",
                        "DocDateTime": "2026-10-24T12:00:00",
                        "OperationType": "Income",
                        "IsBso": False,
                        "IsCorrection": False,
                        "UserInn": "2308139496",
                        "KktRegNumber": REG_NUMBER,
                        "FnNumber": "9999078902009926",
                        "DocNumber": 10,
                        "DecimalFiscalSign": "1001",
                        "TotalSumm": 13000,
                        "CashSumm": 13000,
                        "ECashSumm": 0,
                        "Items": [
                            {
                                "Name": "Кофе",
                                "Price": 13000,
                                "Quantity": 1,
                                "Total": 13000,
                                "Barcode": "0123456789012",
                                "ProductUnitOfMeasure": "0",
                            }
                        ],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ofd_client = OfdClient(http_client=client, settings=settings())
        receipts = await ofd_client.fetch_receipts(
            reg_number=REG_NUMBER,
            date_from=datetime(2026, 10, 24, 0, 0),
            date_to=datetime(2026, 10, 25, 0, 0),
        )

    assert len(receipts) == 1
    assert receipts[0].doc_number == 10
    assert receipts[0].fiscal_sign == "1001"
    assert receipts[0].items[0].barcode == "0123456789012"


async def test_client_raises_on_ofd_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Status": "Failed",
                "Errors": [{"Message": "Нет доступа", "Code": "Forbidden"}],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ofd_client = OfdClient(http_client=client, settings=settings())
        with pytest.raises(OfdApiError):
            await ofd_client.fetch_receipts(
                reg_number=REG_NUMBER,
                date_from=datetime(2026, 10, 24, 0, 0),
                date_to=datetime(2026, 10, 25, 0, 0),
            )


async def test_sync_maps_thirteen_digit_barcode_as_gtin14() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload(barcode="4600000000017")]),
        repository=repository,
        catalog_api=FakeCatalogAPI(by_gtin={"04600000000017": NOMENCLATURE_ID}),
    )

    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    receipt = next(iter(repository.receipts.values()))
    assert receipt.lines[0].nomenclature_id == NOMENCLATURE_ID


async def test_sync_repairs_receipt_waiting_for_location() -> None:
    repository = FakeOfdReceiptRepository()
    service = build_sync_service(
        client=FakeOfdClient([payload()]),
        repository=repository,
        fiscal_api=FakeFiscalAPI(org_unit_id=None),
    )

    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    waiting = next(iter(repository.receipts.values()))
    assert waiting.status is OfdReceiptStatus.NEEDS_LOCATION

    # Привязку кассы настроили — следующая синхронизация подхватит склад.
    service = build_sync_service(
        client=FakeOfdClient([]),
        repository=repository,
        fiscal_api=FakeFiscalAPI(org_unit_id=ORG_UNIT_ID),
    )
    await service.sync(
        reg_number=REG_NUMBER,
        date_from=datetime(2026, 10, 24, 0, 0),
        date_to=datetime(2026, 10, 25, 0, 0),
    )

    repaired = next(iter(repository.receipts.values()))
    assert repaired.org_unit_id == ORG_UNIT_ID
    assert repaired.status is OfdReceiptStatus.NEEDS_MAPPING


async def test_sync_rejects_period_longer_than_31_days() -> None:
    service = build_sync_service(
        client=FakeOfdClient([]),
        repository=FakeOfdReceiptRepository(),
    )

    with pytest.raises(InvalidOfdPeriodError):
        await service.sync(
            reg_number=REG_NUMBER,
            date_from=datetime(2026, 9, 1, 0, 0),
            date_to=datetime(2026, 10, 3, 0, 0),
        )


async def test_sync_rejects_period_before_cutover() -> None:
    service = build_sync_service(
        client=FakeOfdClient([]),
        repository=FakeOfdReceiptRepository(),
        ofd_settings=settings(cutover_date=date(2026, 10, 1)),
    )

    with pytest.raises(OfdPeriodBeforeCutoverError):
        await service.sync(
            reg_number=REG_NUMBER,
            date_from=datetime(2026, 9, 30, 23, 0),
            date_to=datetime(2026, 10, 1, 1, 0),
        )
