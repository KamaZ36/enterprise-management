from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.sqlalchemy import (
    SQLAlchemyOrgUnitRepository,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ofd_receipt import (
    PostOfdReceiptCommand,
    PostOfdReceiptInteractor,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdReceipt,
    OfdReceiptLine,
    OfdReceiptStatus,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.sqlalchemy import (
    SQLAlchemyOfdReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.sales.post_sale import (
    PostSaleCommand,
    PostSaleInteractor,
    SaleLineCommand,
)
from myasnaya_derevnya.modules.inventory.domain.errors import InsufficientStockError
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.sqlalchemy import (
    SQLAlchemyStockPostingRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.helpers import TEST_PREFIX
from tests.modules.inventory.helpers import (
    FakeIdentityProvider,
    FakeStaffAPI,
    build_interactors,
    build_posting,
)

pytestmark = pytest.mark.db

REG_NUMBER = "0000000000051264"
OCCURRED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


class FakeInventoryAPI:
    """Настоящее списание по складу без HTTP-слоя inventory."""

    def __init__(self, session) -> None:
        preconditions, _, ledger = build_posting(session)
        self._post_sale = PostSaleInteractor(
            preconditions=preconditions,
            ledger=ledger,
        )
        self._posting_repository = SQLAlchemyStockPostingRepository(session)

    async def post_sale(
        self,
        *,
        document_id: UUID,
        org_unit_id: UUID,
        occurred_at: datetime,
        lines,
        posted_by: UUID | None = None,
    ) -> None:
        await self._post_sale(
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

    async def sale_posting_exists(self, document_id: UUID) -> bool:
        return await self._posting_repository.exists(
            document_type=DocumentType.SALE,
            document_id=document_id,
        )


@pytest.fixture
async def warehouse(db_session, root_org_unit_id):
    repository = SQLAlchemyOrgUnitRepository(db_session)
    now = get_datetime_utc()
    org_unit = OrgUnit(
        id=uuid4(),
        parent_id=root_org_unit_id,
        type=OrgUnitType.PRODUCTION,
        code=f"{TEST_PREFIX}{uuid4().hex[:8]}",
        name="Склад ОФД",
        address=None,
        phone_number=None,
        timezone=None,
        is_active=True,
        attributes={},
        created_at=now,
        updated_at=now,
    )
    await repository.add(org_unit)
    await db_session.commit()
    return org_unit


async def receive(
    session,
    org_unit_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    unit_cost: str,
) -> None:
    interactors = build_interactors(session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            supplier_name="Поставщик",
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost),
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))


def build_receipt(
    *, org_unit_id: UUID, nomenclature_id: UUID, quantity: str
) -> OfdReceipt:
    receipt_id = uuid4()
    line = OfdReceiptLine.create(
        receipt_id=receipt_id,
        line_number=1,
        name=f"{TEST_PREFIX}Кофе",
        barcode=f"{TEST_PREFIX}4600000000017",
        product_code={},
        quantity=Decimal(quantity),
        unit="0",
        price_kopecks=13000,
        total_kopecks=13000,
        raw={"Name": f"{TEST_PREFIX}Кофе"},
    )
    receipt = OfdReceipt.create(
        receipt_id=receipt_id,
        inn="2308139496",
        reg_number=REG_NUMBER,
        fn_number="9999078902009926",
        doc_number=7,
        fiscal_sign=f"{TEST_PREFIX}7",
        raw_id=f"{TEST_PREFIX}raw-7",
        doc_datetime=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        c_date_utc=datetime(2026, 10, 24, 9, 1, tzinfo=UTC),
        operation_type="Income",
        is_correction=False,
        is_bso=False,
        total_kopecks=13000,
        cash_kopecks=13000,
        ecash_kopecks=0,
        org_unit_id=org_unit_id,
        lines=[line],
        raw={"DocNumber": 7},
    )
    receipt.map_line(line.id, nomenclature_id)
    return receipt


def build_post_interactor(session, repository):
    return PostOfdReceiptInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=FakeStaffAPI(),
        receipt_repository=repository,
        inventory_api=FakeInventoryAPI(session),
        transaction_manager=SQLAlchemyTransactionManager(session),
    )


async def test_post_receipt_deducts_stock_and_is_idempotent(
    db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "10", "100")

    repository = SQLAlchemyOfdReceiptRepository(db_session)
    receipt = build_receipt(
        org_unit_id=warehouse.id,
        nomenclature_id=nomenclature.id,
        quantity="3",
    )
    assert receipt.status is OfdReceiptStatus.READY
    await repository.add_if_absent(receipt)
    await db_session.commit()

    interactor = build_post_interactor(db_session, repository)
    result = await interactor(PostOfdReceiptCommand(receipt_id=receipt.id))
    assert result.status == "posted"

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(7)

    # Повторное проведение не должно списать товар ещё раз.
    result = await interactor(PostOfdReceiptCommand(receipt_id=receipt.id))
    assert result.status == "posted"
    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(7)


async def test_shortage_marks_receipt_failed_and_keeps_stock(
    db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "2", "100")

    repository = SQLAlchemyOfdReceiptRepository(db_session)
    receipt = build_receipt(
        org_unit_id=warehouse.id,
        nomenclature_id=nomenclature.id,
        quantity="5",
    )
    await repository.add_if_absent(receipt)
    await db_session.commit()

    interactor = build_post_interactor(db_session, repository)
    with pytest.raises(InsufficientStockError):
        await interactor(PostOfdReceiptCommand(receipt_id=receipt.id))

    stored = await repository.get_by_id(receipt.id)
    assert stored is not None
    assert stored.status is OfdReceiptStatus.FAILED
    assert stored.error

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(2)

    posting_repository = SQLAlchemyStockPostingRepository(db_session)
    assert not await posting_repository.exists(
        document_type=DocumentType.SALE, document_id=receipt.id
    )
