from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InsufficientStockError,
)
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    SaleLine,
)
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceipt,
    PosReceiptLine,
    PosReceiptStatus,
)

OCCURRED_AT = datetime(2026, 10, 24, 8, 2, 26, tzinfo=UTC)
SOURCE_ID = uuid4()
ORG_UNIT_ID = uuid4()


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeReceiptRepository:
    def __init__(self) -> None:
        self.saved: list[PosReceipt] = []

    async def save(self, receipt: PosReceipt) -> None:
        self.saved.append(receipt)


class FakeInventoryAPI:
    def __init__(self) -> None:
        self.posted: list[tuple[UUID, tuple[SaleLine, ...]]] = []
        self.existing = False
        self.error: Exception | None = None

    async def sale_posting_exists(self, document_id: UUID) -> bool:
        return self.existing

    async def post_sale(self, *, document_id, org_unit_id, occurred_at, lines, posted_by=None):
        if self.error is not None:
            raise self.error
        self.posted.append((org_unit_id, tuple(lines)))
        self.existing = True
        return ()


def build_service():
    repository = FakeReceiptRepository()
    inventory = FakeInventoryAPI()
    transactions = FakeTransactionManager()
    service = ReceiptPostingService(
        receipt_repository=repository,
        inventory_api=inventory,
        transaction_manager=transactions,
    )
    return service, repository, inventory, transactions


def build_receipt(*lines: tuple[UUID | None, Decimal]) -> PosReceipt:
    receipt_id = uuid4()
    receipt_lines = [
        PosReceiptLine.create(
            receipt_id=receipt_id,
            line_number=index,
            external_guid=None,
            product_guid=f"{index:032X}",
            product_name="Товар",
            unit="кг",
            quantity=quantity,
            price_kopecks=10000,
            amount_kopecks=10000,
        )
        for index, (_, quantity) in enumerate(lines, start=1)
    ]

    for line, (nomenclature_id, _) in zip(receipt_lines, lines, strict=True):
        if nomenclature_id is not None:
            line.map_to(nomenclature_id)

    return PosReceipt.create(
        receipt_id=receipt_id,
        source_id=SOURCE_ID,
        agent_id=None,
        batch_id=None,
        external_guid=f"{uuid4().hex}{uuid4().hex}"[:32].upper(),
        occurred_at=OCCURRED_AT,
        kind="sale",
        payment_kind="card",
        total_kopecks=10000,
        subdivision_code=None,
        subdivision_name=None,
        cashier=None,
        shift=None,
        number=None,
        fd_number=None,
        fp_number=None,
        fn_number=None,
        org_unit_id=ORG_UNIT_ID,
        lines=receipt_lines,
    )


async def test_sale_without_tech_card_writes_off_the_product_itself() -> None:
    nomenclature_id = uuid4()
    service, _, inventory, _ = build_service()

    receipt = await service.post(build_receipt((nomenclature_id, Decimal("0.512"))))

    assert receipt.status is PosReceiptStatus.POSTED
    assert len(inventory.posted) == 1
    _, lines = inventory.posted[0]
    assert [(line.nomenclature_id, line.quantity) for line in lines] == [
        (nomenclature_id, Decimal("0.512000"))
    ]


async def test_unmapped_receipt_is_not_posted() -> None:
    service, repository, inventory, transactions = build_service()

    receipt = await service.post(build_receipt((None, Decimal(1))))

    assert receipt.status is PosReceiptStatus.NEEDS_MAPPING
    assert inventory.posted == []
    assert repository.saved[-1].status is PosReceiptStatus.NEEDS_MAPPING
    assert transactions.commits == 1


async def test_return_is_ignored() -> None:
    service, repository, inventory, _ = build_service()
    receipt = build_receipt((uuid4(), Decimal(1)))

    receipt = PosReceipt.create(
        receipt_id=receipt.id,
        source_id=SOURCE_ID,
        agent_id=None,
        batch_id=None,
        external_guid=receipt.external_guid,
        occurred_at=OCCURRED_AT,
        kind="return",
        payment_kind="card",
        total_kopecks=10000,
        subdivision_code=None,
        subdivision_name=None,
        cashier=None,
        shift=None,
        number=None,
        fd_number=None,
        fp_number=None,
        fn_number=None,
        org_unit_id=ORG_UNIT_ID,
        lines=list(receipt.lines),
    )

    posted = await service.post(receipt)

    assert posted.status is PosReceiptStatus.IGNORED
    assert inventory.posted == []
    assert repository.saved[-1].status is PosReceiptStatus.IGNORED


async def test_insufficient_stock_marks_receipt_as_needs_stock() -> None:
    nomenclature_id = uuid4()
    service, repository, inventory, transactions = build_service()
    inventory.error = InsufficientStockError(
        org_unit_id=ORG_UNIT_ID,
        nomenclature_id=nomenclature_id,
        available=Decimal(0),
        requested=Decimal(1),
    )

    receipt = await service.post(build_receipt((nomenclature_id, Decimal(1))))

    assert receipt.status is PosReceiptStatus.NEEDS_STOCK
    assert repository.saved[-1].status is PosReceiptStatus.NEEDS_STOCK
    assert transactions.rollbacks == 1


async def test_other_posting_error_marks_receipt_as_failed() -> None:
    nomenclature_id = uuid4()
    service, repository, inventory, _ = build_service()
    inventory.error = RuntimeError("boom")

    receipt = await service.post(build_receipt((nomenclature_id, Decimal(1))))

    assert receipt.status is PosReceiptStatus.FAILED
    assert repository.saved[-1].status is PosReceiptStatus.FAILED


async def test_already_posted_document_is_marked_posted() -> None:
    nomenclature_id = uuid4()
    service, repository, inventory, _ = build_service()
    inventory.existing = True

    receipt = await service.post(build_receipt((nomenclature_id, Decimal(1))))

    assert receipt.status is PosReceiptStatus.POSTED
    assert inventory.posted == []
    assert repository.saved[-1].status is PosReceiptStatus.POSTED


async def test_document_already_posted_error_is_treated_as_success() -> None:
    nomenclature_id = uuid4()
    service, repository, inventory, _ = build_service()
    inventory.error = DocumentAlreadyPostedError(document_id=uuid4())

    receipt = await service.post(build_receipt((nomenclature_id, Decimal(1))))

    assert receipt.status is PosReceiptStatus.POSTED
    assert repository.saved[-1].status is PosReceiptStatus.POSTED
