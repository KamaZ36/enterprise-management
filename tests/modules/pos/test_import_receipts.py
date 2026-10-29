from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from myasnaya_derevnya.modules.pos.application.dto import (
    IncomingReceipt,
    IncomingReceiptLine,
)
from myasnaya_derevnya.modules.pos.application.interactors.import_receipts import (
    ImportPosReceiptsCommand,
    ImportPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent
from myasnaya_derevnya.modules.pos.domain.entities.product_mapping import (
    PosProductMapping,
)
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceipt,
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.domain.value_objects.api_key import (
    api_key_prefix,
    generate_api_key,
    hash_api_key,
)

OCCURRED_AT = datetime(2026, 10, 24, 8, 2, 26, tzinfo=UTC)
DOKA_ORG_ID = "915612757914"
RECEIPT_GUID = "27DE775614AD4D17A482B578611C605C915612757914"
PRODUCT_GUID = "1A537BD80C2E404890CB98625DB13B3E"


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
        self.receipts: dict[tuple[UUID, str], PosReceipt] = {}
        self.saved: list[PosReceipt] = []

    async def add_if_absent(self, receipt: PosReceipt) -> bool:
        key = (receipt.source_id, receipt.external_guid)
        if key in self.receipts:
            return False
        self.receipts[key] = receipt
        return True

    async def get_by_source_guid(
        self, source_id: UUID, external_guid: str
    ) -> PosReceipt | None:
        return self.receipts.get((source_id, external_guid))

    async def save(self, receipt: PosReceipt) -> None:
        self.saved.append(receipt)

    async def get_by_id(self, receipt_id: UUID) -> PosReceipt | None:
        return next(
            (
                receipt
                for receipt in self.receipts.values()
                if receipt.id == receipt_id
            ),
            None,
        )


class FakeImportBatchRepository:
    def __init__(self) -> None:
        self.batches = []
        self.saved = []

    async def add(self, batch) -> None:
        self.batches.append(batch)

    async def save(self, batch) -> None:
        self.saved.append(batch)


class FakeProductMapRepository:
    def __init__(self, mappings: dict[str, PosProductMapping] | None = None) -> None:
        self._mappings = mappings or {}

    async def mappings_for(self, source_id: UUID, product_guids) -> dict:
        wanted = set(product_guids)
        return {
            guid: mapping
            for guid, mapping in self._mappings.items()
            if guid in wanted
        }


class FakeAgentRepository:
    def __init__(self) -> None:
        self.saved = []

    async def save(self, agent: PosAgent) -> None:
        self.saved.append(agent)


class FakeInventoryAPI:
    def __init__(self) -> None:
        self.posted: list[tuple[UUID, tuple]] = []

    async def sale_posting_exists(self, document_id: UUID) -> bool:
        return any(document_id == item[0] for item in self.posted)

    async def post_sale(
        self, *, document_id, org_unit_id, occurred_at, lines, posted_by=None
    ) -> tuple:
        self.posted.append((document_id, tuple(lines)))
        return ()


class FakeProductionAPI:
    async def recipe_for_output(self, nomenclature_id: UUID, on_date):
        return None


def build_interactor(*, mappings_factory=None):
    transaction_manager = FakeTransactionManager()
    receipt_repository = FakeReceiptRepository()
    batch_repository = FakeImportBatchRepository()
    agent_repository = FakeAgentRepository()
    inventory = FakeInventoryAPI()

    source = PosSource.create(
        doka_org_id=DOKA_ORG_ID,
        name="Кафе",
        org_unit_id=uuid4(),
    )
    mappings = (
        mappings_factory(source.id) if mappings_factory is not None else None
    )

    posting_service = ReceiptPostingService(
        receipt_repository=receipt_repository,
        inventory_api=inventory,
        production_api=FakeProductionAPI(),
        transaction_manager=transaction_manager,
    )
    interactor = ImportPosReceiptsInteractor(
        receipt_repository=receipt_repository,
        import_batch_repository=batch_repository,
        product_map_repository=FakeProductMapRepository(mappings),
        agent_repository=agent_repository,
        posting_service=posting_service,
        transaction_manager=transaction_manager,
    )

    raw_key = generate_api_key()
    agent = PosAgent.create(
        source_id=source.id,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=api_key_prefix(raw_key),
        install_id="install-1",
    )

    return interactor, source, agent, receipt_repository, batch_repository, inventory


def build_incoming(
    *,
    guid: str = RECEIPT_GUID,
    product_guid: str = PRODUCT_GUID,
    kind: str = "sale",
) -> IncomingReceipt:
    return IncomingReceipt(
        guid=guid,
        occurred_at=OCCURRED_AT,
        kind=kind,
        payment_kind="card",
        total_kopecks=25000,
        subdivision_code="1",
        subdivision_name="Торговый зал",
        cashier="Администратор",
        shift="422",
        number="1",
        fd_number="18747",
        fp_number="1603810978",
        fn_number="7380440902472099",
        lines=(
            IncomingReceiptLine(
                guid="A0F13AA47AF4468F8CD2EF7CF14E3674",
                product_guid=product_guid,
                product_name="Медовик",
                unit="кг",
                quantity=Decimal("0.512"),
                price_kopecks=25000,
                amount_kopecks=25000,
                discount_kopecks=0,
                barcode=None,
                mark_code=None,
            ),
        ),
    )


def build_command(source, agent, *receipts) -> ImportPosReceiptsCommand:
    return ImportPosReceiptsCommand(
        source=source,
        agent=agent,
        file_name="Обмен_Продаж_360900586761_27.10.2026_17.56.45.xml",
        file_sha256="a" * 64,
        exported_at=OCCURRED_AT,
        receipts=tuple(receipts),
    )


async def test_unmapped_receipt_is_stored_and_reported_as_pending() -> None:
    interactor, source, agent, receipts, batches, inventory = build_interactor()

    result = await interactor(build_command(source, agent, build_incoming()))

    assert [item.status for item in result.results] == ["pending_unmapped"]
    assert inventory.posted == []
    stored = next(iter(receipts.receipts.values()))
    assert stored.status is PosReceiptStatus.NEEDS_MAPPING
    assert batches.batches[0].receipts_created == 1
    assert batches.batches[0].receipts_pending == 1
    assert batches.batches[0].status == "completed"
    assert agent.last_success_at is not None


async def test_mapped_receipt_is_posted_immediately() -> None:
    def mapping_for(source_id: UUID) -> dict[str, PosProductMapping]:
        mapping = PosProductMapping.create(
            source_id=source_id,
            doka_product_guid=PRODUCT_GUID,
            nomenclature_id=uuid4(),
            unit_factor=Decimal("0.001"),
        )
        return {PRODUCT_GUID: mapping}

    interactor, source, agent, _receipts, batches, inventory = build_interactor(
        mappings_factory=mapping_for
    )

    result = await interactor(build_command(source, agent, build_incoming()))

    assert [item.status for item in result.results] == ["posted"]
    assert len(inventory.posted) == 1
    _, lines = inventory.posted[0]
    assert lines[0].quantity == Decimal("0.000512")
    assert batches.batches[0].receipts_posted == 1


async def test_repeated_import_is_deduplicated_by_guid() -> None:
    interactor, source, agent, receipts, _batches, inventory = build_interactor()
    command = build_command(source, agent, build_incoming())

    first = await interactor(command)
    second = await interactor(command)

    assert [item.status for item in first.results] == ["pending_unmapped"]
    assert [item.status for item in second.results] == ["duplicate"]
    assert len(receipts.receipts) == 1
    assert inventory.posted == []


async def test_one_broken_receipt_does_not_break_the_batch() -> None:
    interactor, source, agent, receipts, batches, _inventory = build_interactor()
    broken = build_incoming(guid="not-a-guid")

    result = await interactor(
        build_command(source, agent, broken, build_incoming())
    )

    assert [item.status for item in result.results] == [
        "rejected",
        "pending_unmapped",
    ]
    assert batches.batches[0].receipts_failed == 1
    assert len(receipts.receipts) == 1


async def test_return_receipt_is_stored_but_not_posted() -> None:
    interactor, source, agent, receipts, _batches, inventory = build_interactor()

    result = await interactor(
        build_command(source, agent, build_incoming(kind="return"))
    )

    assert [item.status for item in result.results] == ["rejected"]
    stored = next(iter(receipts.receipts.values()))
    assert stored.status is PosReceiptStatus.IGNORED
    assert inventory.posted == []
