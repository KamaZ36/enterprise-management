from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.production.post_production import (
    PostedProduction,
    PostedProductionReceipt,
)
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import LocationInfo
from myasnaya_derevnya.modules.production.application.dto import (
    ProductionOrderListItem,
    ProductionOrderPage,
)
from myasnaya_derevnya.modules.production.application.interactors.cancel_production_order import (
    CancelProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.create_production_order import (
    CreateProductionOrderCommand,
    CreateProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.get_production_order import (
    GetProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.list_production_orders import (
    ListProductionOrdersInteractor,
    ListProductionOrdersQuery,
)
from myasnaya_derevnya.modules.production.application.interactors.post_production_order import (
    PostProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.update_production_order import (
    ProductionOrderActualCommand,
    UpdateProductionOrderCommand,
    UpdateProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
)
from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionLocationNotFoundError,
    ProductionOrderNotDraftError,
    ProductionOrderNotFoundError,
    TechCardNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import (
    MANAGE_ORDERS,
    POST_ORDER,
    READ_ORDERS,
)
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.fakes import (
    FakeIdentityProvider,
    FakeStaffAPI,
    FakeTransactionManager,
)

COMPONENT_ID = uuid4()
OUTPUT_ID = uuid4()


class FakeInventoryAPI:
    def __init__(self) -> None:
        self.locations: dict[UUID, LocationInfo] = {}
        self.locations_list: list[LocationInfo] = []
        self.posted: PostedProduction | None = None
        self.post_calls: list[dict] = []

    async def get_location(self, org_unit_id: UUID) -> LocationInfo | None:
        return self.locations.get(org_unit_id)

    async def list_locations(self) -> list[LocationInfo]:
        return self.locations_list

    async def post_production(self, **kwargs) -> PostedProduction:
        self.post_calls.append(kwargs)
        assert self.posted is not None
        return self.posted


class FakeCatalogAPI:
    def __init__(self, names: dict[UUID, str] | None = None) -> None:
        self.names = names or {}
        self.asked: list[list] = []

    async def nomenclature_names(self, nomenclature_ids):
        self.asked.append(list(nomenclature_ids))
        return self.names


class FakeTechCardRepository:
    def __init__(self, card: TechCard | None) -> None:
        self.card = card

    async def get_by_id(self, tech_card_id):
        return self.card


class FakeOrderRepository:
    def __init__(self, order: ProductionOrder | None) -> None:
        self.order = order
        self.added: list[ProductionOrder] = []
        self.saved: list[ProductionOrder] = []

    async def get_by_id(self, order_id):
        return self.order

    async def add(self, order: ProductionOrder) -> None:
        self.added.append(order)

    async def save(self, order: ProductionOrder) -> None:
        self.saved.append(order)


class FakeOrderReader:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.items: list[ProductionOrderListItem] = []
        self.total = 0

    async def list(self, **kwargs):
        self.calls.append(kwargs)
        return self.items, self.total


def make_card() -> TechCard:
    return TechCard.create(
        code="PYTEST-CARD",
        name="Копчение",
        basis=TechCardBasis.INPUT,
        lines=[
            TechCardLine.component(
                nomenclature_id=COMPONENT_ID, quantity=Decimal(100)
            ),
            TechCardLine.output(
                nomenclature_id=OUTPUT_ID,
                quantity=Decimal(40),
                output_kind=OutputKind.MAIN,
            ),
        ],
    )


def make_order(*, org_unit_id: UUID | None = None) -> ProductionOrder:
    return ProductionOrder.create(
        org_unit_id=org_unit_id or uuid4(),
        tech_card=make_card(),
        batch_count=Decimal(1),
        occurred_at=get_datetime_utc(),
        created_by=uuid4(),
    )


def location(name: str = "Цех") -> LocationInfo:
    return LocationInfo(id=uuid4(), name=name, is_active=True)


def build_create(*, allowed: bool = True, card: TechCard | None, loc=None):
    inventory = FakeInventoryAPI()
    if loc is not None:
        inventory.locations[loc.id] = loc
    repository = FakeOrderRepository(None)
    staff_api = FakeStaffAPI(allowed=allowed)
    transactions = FakeTransactionManager()
    interactor = CreateProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        tech_card_repository=FakeTechCardRepository(card),
        order_repository=repository,
        transaction_manager=transactions,
    )

    return interactor, repository, staff_api, inventory, transactions


async def test_create_unknown_card_is_reported() -> None:
    interactor, repository, _, _, _ = build_create(card=None)

    with pytest.raises(TechCardNotFoundError):
        await interactor(
            CreateProductionOrderCommand(
                org_unit_id=uuid4(),
                tech_card_id=uuid4(),
                batch_count=Decimal(1),
                occurred_at=get_datetime_utc(),
            )
        )

    assert repository.added == []


async def test_create_unknown_location_is_reported() -> None:
    interactor, repository, _, _, _ = build_create(card=make_card())

    with pytest.raises(ProductionLocationNotFoundError):
        await interactor(
            CreateProductionOrderCommand(
                org_unit_id=uuid4(),
                tech_card_id=uuid4(),
                batch_count=Decimal(1),
                occurred_at=get_datetime_utc(),
            )
        )

    assert repository.added == []


async def test_create_requires_manage_orders_at_location() -> None:
    card = make_card()
    point = location()
    interactor, repository, staff_api, _, _ = build_create(
        allowed=False, card=card, loc=point
    )

    with pytest.raises(ForbiddenError):
        await interactor(
            CreateProductionOrderCommand(
                org_unit_id=point.id,
                tech_card_id=card.id,
                batch_count=Decimal(1),
                occurred_at=get_datetime_utc(),
            )
        )

    assert staff_api.checked == [(MANAGE_ORDERS.code, point.id)]
    assert repository.added == []


async def test_create_adds_order_and_commits() -> None:
    card = make_card()
    point = location()
    interactor, repository, _, _, transactions = build_create(card=card, loc=point)

    order_id = await interactor(
        CreateProductionOrderCommand(
            org_unit_id=point.id,
            tech_card_id=card.id,
            batch_count=Decimal(2),
            occurred_at=get_datetime_utc(),
        )
    )

    assert len(repository.added) == 1
    assert repository.added[0].id == order_id
    assert repository.added[0].batch_count == Decimal(2)
    assert transactions.commits == 1


def build_on_order(*, order: ProductionOrder | None, allowed: bool = True, loc=None):
    inventory = FakeInventoryAPI()
    if loc is not None:
        inventory.locations[loc.id] = loc
    repository = FakeOrderRepository(order)
    staff_api = FakeStaffAPI(allowed=allowed)
    transactions = FakeTransactionManager()

    return inventory, repository, staff_api, transactions


async def test_update_unknown_order_is_reported() -> None:
    inventory, repository, staff_api, transactions = build_on_order(order=None)
    interactor = UpdateProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_repository=repository,
        transaction_manager=transactions,
    )

    with pytest.raises(ProductionOrderNotFoundError):
        await interactor(
            UpdateProductionOrderCommand(order_id=uuid4(), actuals=())
        )


async def test_update_requires_manage_orders() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    inventory, repository, staff_api, transactions = build_on_order(
        order=order, allowed=False, loc=point
    )
    interactor = UpdateProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_repository=repository,
        transaction_manager=transactions,
    )

    with pytest.raises(ForbiddenError):
        await interactor(
            UpdateProductionOrderCommand(
                order_id=order.id,
                actuals=(
                    ProductionOrderActualCommand(
                        line_id=order.outputs[0].id, quantity=Decimal(10)
                    ),
                ),
            )
        )

    assert staff_api.checked == [(MANAGE_ORDERS.code, point.id)]
    assert repository.saved == []


async def test_update_applies_actuals_and_commits() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    inventory, repository, staff_api, transactions = build_on_order(
        order=order, loc=point
    )
    output_line = order.outputs[0]
    interactor = UpdateProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_repository=repository,
        transaction_manager=transactions,
    )

    await interactor(
        UpdateProductionOrderCommand(
            order_id=order.id,
            actuals=(
                ProductionOrderActualCommand(
                    line_id=output_line.id, quantity=Decimal(30)
                ),
            ),
        )
    )

    assert order.outputs[0].actual_quantity == Decimal(30)
    assert repository.saved == [order]
    assert transactions.commits == 1


def build_cancel(*, order: ProductionOrder | None, allowed: bool = True, loc=None):
    inventory, repository, staff_api, transactions = build_on_order(
        order=order, allowed=allowed, loc=loc
    )
    interactor = CancelProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_repository=repository,
        transaction_manager=transactions,
    )

    return interactor, repository, transactions


async def test_cancel_unknown_order_is_reported() -> None:
    interactor, _, _ = build_cancel(order=None)

    with pytest.raises(ProductionOrderNotFoundError):
        await interactor(uuid4())


async def test_cancel_marks_order_and_commits() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    interactor, repository, transactions = build_cancel(order=order, loc=point)

    await interactor(order.id)

    assert order.status is ProductionOrderStatus.CANCELLED
    assert repository.saved == [order]
    assert transactions.commits == 1


def build_post(*, order: ProductionOrder | None, allowed: bool = True, loc=None):
    inventory, repository, staff_api, transactions = build_on_order(
        order=order, allowed=allowed, loc=loc
    )
    interactor = PostProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_repository=repository,
        transaction_manager=transactions,
    )

    return interactor, repository, inventory, staff_api, transactions


async def test_post_requires_post_permission() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    interactor, repository, inventory, staff_api, _ = build_post(
        order=order, allowed=False, loc=point
    )

    with pytest.raises(ForbiddenError):
        await interactor(order.id)

    assert staff_api.checked == [(POST_ORDER.code, point.id)]
    assert inventory.post_calls == []
    assert repository.saved == []


async def test_post_posts_to_inventory_and_applies_costs() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    output_line = order.outputs[0]
    order.set_actual(output_line.id, Decimal(30))
    interactor, repository, inventory, _, transactions = build_post(
        order=order, loc=point
    )
    inventory.posted = PostedProduction(
        issued_cost_kopecks=40000,
        receipts=(
            PostedProductionReceipt(
                nomenclature_id=OUTPUT_ID,
                quantity=Decimal(30),
                cost_kopecks=12345,
                lot_id=uuid4(),
            ),
        ),
    )

    await interactor(order.id)

    assert len(inventory.post_calls) == 1
    call = inventory.post_calls[0]
    assert call["document_id"] == order.id
    assert call["org_unit_id"] == point.id
    assert [issue.nomenclature_id for issue in call["issues"]] == [COMPONENT_ID]
    assert [receipt.nomenclature_id for receipt in call["receipts"]] == [OUTPUT_ID]
    assert call["receipts"][0].lot_code.startswith("PYTEST-CARD-")
    assert order.outputs[0].cost_kopecks == 12345
    assert order.status is ProductionOrderStatus.POSTED
    assert repository.saved == [order]
    assert transactions.commits == 1


async def test_post_rejects_posted_order() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    order.post()
    interactor, _, _, _, _ = build_post(order=order, loc=point)

    with pytest.raises(ProductionOrderNotDraftError):
        await interactor(order.id)


def build_get(*, order: ProductionOrder | None, allowed: bool = True, loc=None):
    inventory, repository, staff_api, _ = build_on_order(
        order=order, allowed=allowed, loc=loc
    )
    catalog_api = FakeCatalogAPI()
    interactor = GetProductionOrderInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_repository=repository,
        catalog_api=catalog_api,
    )

    return interactor, staff_api, catalog_api


async def test_get_unknown_order_is_reported() -> None:
    interactor, _, _ = build_get(order=None)

    with pytest.raises(ProductionOrderNotFoundError):
        await interactor(uuid4())


async def test_get_requires_read_orders() -> None:
    point = location()
    order = make_order(org_unit_id=point.id)
    interactor, staff_api, _ = build_get(order=order, allowed=False, loc=point)

    with pytest.raises(ForbiddenError):
        await interactor(order.id)

    assert staff_api.checked == [(READ_ORDERS.code, point.id)]


async def test_get_returns_detail_with_location_and_names() -> None:
    point = location(name="Коптильня")
    order = make_order(org_unit_id=point.id)
    interactor, _, catalog_api = build_get(order=order, loc=point)
    catalog_api.names = {COMPONENT_ID: "Говядина", OUTPUT_ID: "Лопатка"}

    detail = await interactor(order.id)

    assert detail.id == order.id
    assert detail.location_name == "Коптильня"
    names = {line.nomenclature_name for line in detail.lines}
    assert names == {"Говядина", "Лопатка"}


def build_list(*, scope: AccessScope, locs: list[LocationInfo]):
    inventory = FakeInventoryAPI()
    inventory.locations_list = locs
    for item in locs:
        inventory.locations[item.id] = item
    reader = FakeOrderReader()
    staff_api = FakeStaffAPI(scope=scope)
    interactor = ListProductionOrdersInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        inventory_api=inventory,
        order_reader=reader,
    )

    return interactor, reader, staff_api


async def test_list_empty_scope_is_forbidden() -> None:
    interactor, reader, _ = build_list(scope=AccessScope.of([]), locs=[location()])

    with pytest.raises(ForbiddenError):
        await interactor(ListProductionOrdersQuery())

    assert reader.calls == []


async def test_list_checks_read_orders_scope() -> None:
    interactor, _, staff_api = build_list(
        scope=AccessScope.company_wide(), locs=[]
    )

    await interactor(ListProductionOrdersQuery())

    assert staff_api.scope_checked == [READ_ORDERS.code]


async def test_list_company_wide_sees_all_locations() -> None:
    interactor, reader, _ = build_list(
        scope=AccessScope.company_wide(), locs=[location(), location()]
    )

    page = await interactor(ListProductionOrdersQuery())

    assert isinstance(page, ProductionOrderPage)
    assert reader.calls[0]["org_unit_ids"] is None


async def test_list_restricted_scope_filters_locations() -> None:
    mine = location("Мой цех")
    other = location("Чужой цех")
    interactor, reader, _ = build_list(
        scope=AccessScope.of([mine.id]), locs=[mine, other]
    )

    await interactor(ListProductionOrdersQuery())

    assert reader.calls[0]["org_unit_ids"] == [mine.id]


async def test_list_requested_point_outside_scope_is_forbidden() -> None:
    mine = location("Мой цех")
    other = location("Чужой цех")
    interactor, reader, _ = build_list(
        scope=AccessScope.of([mine.id]), locs=[mine, other]
    )

    with pytest.raises(ForbiddenError):
        await interactor(ListProductionOrdersQuery(org_unit_id=other.id))

    assert reader.calls == []


async def test_list_attaches_location_name() -> None:
    point = location("Коптильня")
    interactor, reader, _ = build_list(
        scope=AccessScope.company_wide(), locs=[point]
    )
    item = ProductionOrderListItem(
        id=uuid4(),
        org_unit_id=point.id,
        tech_card_id=uuid4(),
        tech_card_code="PYTEST-CARD",
        tech_card_version=1,
        status=ProductionOrderStatus.DRAFT,
        occurred_at=get_datetime_utc(),
        batch_count=Decimal(1),
        created_at=get_datetime_utc(),
    )
    reader.items = [item]
    reader.total = 1

    page = await interactor(ListProductionOrdersQuery())

    assert page.items[0].location_name == "Коптильня"
    assert page.items[0].id == item.id
