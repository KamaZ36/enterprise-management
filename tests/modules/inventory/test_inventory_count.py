from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.interactors.get_point_prices import (
    GetPointPricesInteractor,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.sqlalchemy import (
    SQLAlchemyPriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.sqlalchemy import (
    SQLAlchemyPriceListBindingRepository,
)
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.create import (
    CreateInventoryCountCommand,
    CreateInventoryCountInteractor,
    InventoryCountLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.get import (
    GetInventoryCountInteractor,
    GetInventoryCountQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.list import (
    ListInventoryCountsInteractor,
    ListInventoryCountsQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.post import (
    PostInventoryCountCommand,
    PostInventoryCountInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.update import (
    UpdateInventoryCountCommand,
    UpdateInventoryCountInteractor,
    UpdateInventoryCountLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.entities.inventory_count import (
    InventoryCount,
    InventoryCountLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    EmptyDocumentError,
    NegativeCountError,
    StockLotNotFoundError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.inventory_count.sqlalchemy import (
    SQLAlchemyInventoryCountReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.sqlalchemy import (
    SQLAlchemyInventoryCountRepository,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.inventory.helpers import (
    FakeIdentityProvider,
    FakeStaffAPI,
    build_interactors,
    build_posting,
    business_api,
)

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


def build_catalog_api(session: AsyncSession) -> CatalogAPI:
    return CatalogAPI(
        get_point_prices_interactor=GetPointPricesInteractor(
            binding_repository=SQLAlchemyPriceListBindingRepository(session),
            price_repository=SQLAlchemyPriceRepository(session),
        ),
        nomenclature_repository=SQLAlchemyNomenclatureRepository(session),
    )


def build_inventory_count_interactors(
    session: AsyncSession,
    *,
    allowed: bool = True,
    scope: AccessScope | None = None,
):
    identity = FakeIdentityProvider(uuid4())
    staff_api = FakeStaffAPI(allowed=allowed, scope=scope)
    transaction_manager = SQLAlchemyTransactionManager(session)
    api = business_api(session)
    repository = SQLAlchemyInventoryCountRepository(session)
    preconditions, lot_resolver, ledger = build_posting(session)

    create = CreateInventoryCountInteractor(
        identity_provider=identity,
        business_api=api,
        inventory_count_repository=repository,
        staff_api=staff_api,
        transaction_manager=transaction_manager,
    )
    post = PostInventoryCountInteractor(
        identity_provider=identity,
        inventory_count_repository=repository,
        staff_api=staff_api,
        preconditions=preconditions,
        lot_resolver=lot_resolver,
        ledger=ledger,
        transaction_manager=transaction_manager,
    )
    update = UpdateInventoryCountInteractor(
        identity_provider=identity,
        business_api=api,
        inventory_count_repository=repository,
        staff_api=staff_api,
        transaction_manager=transaction_manager,
    )

    reader = SQLAlchemyInventoryCountReader(session)
    document_scope = DocumentScope(
        identity_provider=identity,
        business_api=api,
        staff_api=staff_api,
    )
    list_interactor = ListInventoryCountsInteractor(
        inventory_count_reader=reader,
        document_scope=document_scope,
    )
    get_interactor = GetInventoryCountInteractor(
        inventory_count_reader=reader,
        catalog_api=build_catalog_api(session),
        document_scope=document_scope,
    )

    return create, post, update, list_interactor, get_interactor, staff_api


async def receive(
    db_session: AsyncSession,
    org_unit_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    unit_cost: str,
    lot_code: str | None = None,
) -> None:
    interactors = build_interactors(db_session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost),
                    lot_code=lot_code,
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))


async def create_count(
    db_session: AsyncSession,
    org_unit_id: UUID,
    lines: list[tuple[UUID, str, str | None]],
) -> UUID:
    create, *_ = build_inventory_count_interactors(db_session)

    return await create(
        CreateInventoryCountCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            comment="Плановая инвентаризация",
            lines=[
                InventoryCountLineCommand(
                    nomenclature_id=nomenclature_id,
                    counted_quantity=Decimal(counted),
                    lot_code=lot_code,
                )
                for nomenclature_id, counted, lot_code in lines
            ],
        )
    )


async def movement_rows(db_session: AsyncSession, document_id: UUID):
    return (
        await db_session.execute(
            text(
                "select movement_type, quantity, total_cost"
                " from inventory.stock_movements"
                " where posting_id in ("
                "   select id from inventory.stock_postings where document_id = :id"
                " ) order by movement_type"
            ),
            {"id": document_id},
        )
    ).all()


async def balance_row(db_session: AsyncSession, org_unit_id: UUID, nomenclature_id: UUID):
    return (
        await db_session.execute(
            text(
                "select quantity, total_value, average_unit_cost"
                " from inventory.stock_balances"
                " where org_unit_id = :org_unit_id and nomenclature_id = :nomenclature_id"
            ),
            {"org_unit_id": org_unit_id, "nomenclature_id": nomenclature_id},
        )
    ).one()


# --- домен ---


def make_line(counted: str = "3") -> InventoryCountLine:
    return InventoryCountLine.create(
        nomenclature_id=uuid4(), counted_quantity=Decimal(counted)
    )


def test_new_inventory_count_is_draft() -> None:
    inventory_count = InventoryCount.create(
        org_unit_id=uuid4(), occurred_at=get_datetime_utc(), lines=[make_line()]
    )

    assert inventory_count.status is DocumentStatus.DRAFT
    assert inventory_count.is_draft is True
    assert inventory_count.posted_at is None


def test_counted_quantity_can_be_zero() -> None:
    line = make_line(counted="0")

    assert line.counted_quantity == Decimal(0)


def test_negative_counted_quantity_is_rejected() -> None:
    with pytest.raises(NegativeCountError):
        make_line(counted="-1")


def test_post_marks_inventory_count_posted() -> None:
    inventory_count = InventoryCount.create(
        org_unit_id=uuid4(), occurred_at=get_datetime_utc(), lines=[make_line()]
    )

    inventory_count.post()

    assert inventory_count.status is DocumentStatus.POSTED
    assert inventory_count.posted_at is not None


def test_second_post_is_rejected() -> None:
    inventory_count = InventoryCount.create(
        org_unit_id=uuid4(), occurred_at=get_datetime_utc(), lines=[make_line()]
    )
    inventory_count.post()

    with pytest.raises(DocumentAlreadyPostedError):
        inventory_count.post()


def test_post_without_lines_is_rejected() -> None:
    inventory_count = InventoryCount.create(
        org_unit_id=uuid4(), occurred_at=get_datetime_utc(), lines=[]
    )

    with pytest.raises(EmptyDocumentError):
        inventory_count.post()


def test_revise_replaces_lines_on_draft() -> None:
    inventory_count = InventoryCount.create(
        org_unit_id=uuid4(), occurred_at=get_datetime_utc(), lines=[make_line("1")]
    )

    inventory_count.revise(
        occurred_at=OCCURRED_AT, comment="Уточнили", lines=[make_line("5")]
    )

    assert inventory_count.comment == "Уточнили"
    assert [line.counted_quantity for line in inventory_count.lines] == [Decimal(5)]


def test_revise_of_posted_document_is_rejected() -> None:
    inventory_count = InventoryCount.create(
        org_unit_id=uuid4(), occurred_at=get_datetime_utc(), lines=[make_line()]
    )
    inventory_count.post()

    with pytest.raises(DocumentAlreadyPostedError):
        inventory_count.revise(
            occurred_at=OCCURRED_AT, comment=None, lines=[make_line("2")]
        )


def test_naive_occurred_at_is_rejected() -> None:
    with pytest.raises(TimezoneRequiredError):
        InventoryCount.create(
            org_unit_id=uuid4(),
            occurred_at=datetime(2026, 10, 19, 12, 0),
            lines=[make_line()],
        )


# --- интеграция ---


async def test_surplus_is_received_at_average_cost(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    await receive(db_session, location.id, nomenclature.id, "10", "100")

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "12", None)]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)
    await post(PostInventoryCountCommand(inventory_count_id=count_id))

    row = await balance_row(db_session, location.id, nomenclature.id)

    assert row.quantity == Decimal(12)
    assert row.total_value == 120000
    assert row.average_unit_cost == Decimal(100)

    movements = await movement_rows(db_session, count_id)
    assert [(m.movement_type, m.quantity, m.total_cost) for m in movements] == [
        ("inventory_surplus", Decimal(2), 20000)
    ]


async def test_shortage_is_issued_at_average_cost(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    await receive(db_session, location.id, nomenclature.id, "10", "100")

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "7", None)]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)
    await post(PostInventoryCountCommand(inventory_count_id=count_id))

    row = await balance_row(db_session, location.id, nomenclature.id)

    assert row.quantity == Decimal(7)
    assert row.total_value == 70000

    movements = await movement_rows(db_session, count_id)
    assert [(m.movement_type, m.quantity, m.total_cost) for m in movements] == [
        ("inventory_shortage", Decimal(-3), -30000)
    ]


async def test_matching_count_produces_no_movements(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    await receive(db_session, location.id, nomenclature.id, "10", "100")

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "10", None)]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)
    await post(PostInventoryCountCommand(inventory_count_id=count_id))

    assert await movement_rows(db_session, count_id) == []


async def test_count_to_zero_zeroes_stock(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    await receive(db_session, location.id, nomenclature.id, "2", "100")

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "0", None)]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)
    await post(PostInventoryCountCommand(inventory_count_id=count_id))

    row = await balance_row(db_session, location.id, nomenclature.id)

    assert row.quantity == Decimal(0)
    assert row.total_value == 0


async def test_surplus_creates_lot(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "4", "LOT-NEW")]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)
    await post(PostInventoryCountCommand(inventory_count_id=count_id))

    rows = (
        await db_session.execute(
            text(
                "select quantity from inventory.stock_lot_balances"
                " where org_unit_id = :org_unit_id and nomenclature_id = :nomenclature_id"
            ),
            {"org_unit_id": location.id, "nomenclature_id": nomenclature.id},
        )
    ).all()

    assert [row.quantity for row in rows] == [Decimal(4)]


async def test_shortage_with_unknown_lot_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    await receive(db_session, location.id, nomenclature.id, "2", "100")

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "0", "MISSING-LOT")]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)

    with pytest.raises(StockLotNotFoundError):
        await post(PostInventoryCountCommand(inventory_count_id=count_id))


async def test_count_cannot_be_posted_twice(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "1", None)]
    )
    _, post, *_ = build_inventory_count_interactors(db_session)
    await post(PostInventoryCountCommand(inventory_count_id=count_id))

    with pytest.raises(DocumentAlreadyPostedError):
        await post(PostInventoryCountCommand(inventory_count_id=count_id))


async def test_post_requires_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "1", None)]
    )
    _, post, *_ = build_inventory_count_interactors(db_session, allowed=False)

    with pytest.raises(ForbiddenError):
        await post(PostInventoryCountCommand(inventory_count_id=count_id))


async def test_update_draft_replaces_lines(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    first = await make_nomenclature()
    second = await make_nomenclature()

    count_id = await create_count(db_session, location.id, [(first.id, "1", None)])
    _, _, update, _, get_interactor, _ = build_inventory_count_interactors(db_session)

    await update(
        UpdateInventoryCountCommand(
            inventory_count_id=count_id,
            occurred_at=OCCURRED_AT,
            comment="Пересчитали",
            lines=[
                UpdateInventoryCountLineCommand(
                    nomenclature_id=second.id,
                    counted_quantity=Decimal(3),
                )
            ],
        )
    )

    detail = await get_interactor(GetInventoryCountQuery(inventory_count_id=count_id))

    assert detail.comment == "Пересчитали"
    assert [line.nomenclature_id for line in detail.lines] == [second.id]
    assert [line.counted_quantity for line in detail.lines] == [Decimal(3)]


async def test_list_returns_created_count(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    count_id = await create_count(
        db_session, location.id, [(nomenclature.id, "1", None)]
    )
    _, _, _, list_interactor, _, _ = build_inventory_count_interactors(db_session)

    page = await list_interactor(ListInventoryCountsQuery())

    assert [item.id for item in page.items] == [count_id]
    assert page.items[0].line_count == 1


async def test_list_respects_scope(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    allowed_location = await make_location()
    hidden_location = await make_location()
    nomenclature = await make_nomenclature()

    await create_count(db_session, hidden_location.id, [(nomenclature.id, "1", None)])

    _, _, _, list_interactor, _, _ = build_inventory_count_interactors(
        db_session, scope=AccessScope.of([allowed_location.id])
    )

    page = await list_interactor(ListInventoryCountsQuery())

    assert page.items == []
