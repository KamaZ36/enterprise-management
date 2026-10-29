from decimal import Decimal
from uuid import UUID, uuid7

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.orders.application.interactors.get_cart import (
    GetCartInteractor,
    GetCartQuery,
)
from myasnaya_derevnya.modules.orders.application.interactors.submit_cart import (
    SubmitCartCommand,
    SubmitCartInteractor,
)
from myasnaya_derevnya.modules.orders.application.interactors.update_cart import (
    CartLineCommand,
    UpdateCartCommand,
    UpdateCartInteractor,
)
from myasnaya_derevnya.modules.orders.domain.entities.order import Order
from myasnaya_derevnya.modules.orders.domain.errors import (
    EmptyCartError,
    NotSoldAtPointError,
)
from myasnaya_derevnya.modules.orders.domain.value_objects.fulfillment import (
    FulfillmentType,
)
from myasnaya_derevnya.modules.orders.domain.value_objects.order_status import (
    OrderStatus,
)
from myasnaya_derevnya.modules.orders.domain.value_objects.payment import PaymentMethod


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeCustomerAPI:
    def __init__(self, profiles: dict[UUID, UUID]) -> None:
        self._profiles = profiles

    async def get_customer_id(self, user_id: UUID) -> UUID | None:
        return self._profiles.get(user_id)


class FakeCatalogAPI:
    def __init__(self, prices: dict[UUID, int]) -> None:
        self._prices = prices

    def set_price(self, nomenclature_id: UUID, price: int) -> None:
        self._prices[nomenclature_id] = price

    async def prices_for_point(
        self, org_unit_id: UUID, nomenclature_ids: list[UUID]
    ) -> dict[UUID, int]:
        return {
            nid: self._prices[nid] for nid in nomenclature_ids if nid in self._prices
        }


class FakeOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[UUID, Order] = {}
        self.saved = 0
        self.added = 0
        self.numbers = 0

    async def add(self, order: Order) -> None:
        self.orders[order.id] = order
        self.added += 1

    async def save(self, order: Order) -> None:
        self.orders[order.id] = order
        self.saved += 1

    async def get_by_id(self, order_id: UUID) -> Order | None:
        return self.orders.get(order_id)

    async def get_open_draft(
        self, customer_id: UUID, org_unit_id: UUID
    ) -> Order | None:
        for order in self.orders.values():
            if (
                order.customer_id == customer_id
                and order.org_unit_id == org_unit_id
                and order.status is OrderStatus.DRAFT
            ):
                return order

        return None

    async def next_number(self, org_unit_id: UUID, day: object) -> int:
        self.numbers += 1

        return self.numbers


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class CartService:
    def __init__(
        self,
        repository: FakeOrderRepository,
        transactions: FakeTransactionManager,
        catalog: FakeCatalogAPI,
        get_cart: GetCartInteractor,
        update_cart: UpdateCartInteractor,
        submit_cart: SubmitCartInteractor,
    ) -> None:
        self.repository = repository
        self.transactions = transactions
        self.catalog = catalog
        self.get_cart = get_cart
        self.update_cart = update_cart
        self.submit_cart = submit_cart


def build(
    *,
    user_id: UUID,
    profiles: dict[UUID, UUID] | None = None,
    prices: dict[UUID, int] | None = None,
) -> CartService:
    repository = FakeOrderRepository()
    transactions = FakeTransactionManager()
    identity = FakeIdentityProvider(user_id)
    customers = FakeCustomerAPI(profiles or {})
    catalog = FakeCatalogAPI(prices or {})

    return CartService(
        repository=repository,
        transactions=transactions,
        catalog=catalog,
        get_cart=GetCartInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            customer_api=customers,  # type: ignore[arg-type]
        ),
        update_cart=UpdateCartInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            catalog_api=catalog,  # type: ignore[arg-type]
            customer_api=customers,  # type: ignore[arg-type]
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
        submit_cart=SubmitCartInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            catalog_api=catalog,  # type: ignore[arg-type]
            customer_api=customers,  # type: ignore[arg-type]
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
    )


async def test_empty_cart_has_defaults() -> None:
    user_id, customer_id = uuid7(), uuid7()
    service = build(user_id=user_id, profiles={user_id: customer_id})
    org_unit_id = uuid7()

    cart = await service.get_cart(GetCartQuery(org_unit_id=org_unit_id))

    assert cart.id is None
    assert cart.lines == []
    assert cart.total == 0
    assert cart.fulfillment_type == FulfillmentType.PICKUP
    assert cart.payment_method == PaymentMethod.ON_PICKUP


async def test_update_cart_creates_draft_and_prices_lines() -> None:
    user_id, customer_id, naam_id = uuid7(), uuid7(), uuid7()
    service = build(
        user_id=user_id, profiles={user_id: customer_id}, prices={naam_id: 45000}
    )
    org_unit_id = uuid7()

    cart = await service.update_cart(
        UpdateCartCommand(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.PICKUP,
            lines=(CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(2)),),
        )
    )

    assert cart.id is not None
    assert cart.total == 90000
    assert cart.lines[0].unit_price == 45000
    assert service.repository.added == 1
    assert service.transactions.commits == 1
    assert service.repository.orders[cart.id].status is OrderStatus.DRAFT


async def test_update_cart_sums_duplicate_lines() -> None:
    user_id, customer_id, naam_id = uuid7(), uuid7(), uuid7()
    service = build(
        user_id=user_id, profiles={user_id: customer_id}, prices={naam_id: 10000}
    )

    cart = await service.update_cart(
        UpdateCartCommand(
            org_unit_id=uuid7(),
            fulfillment_type=FulfillmentType.PICKUP,
            lines=(
                CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(1)),
                CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(2)),
            ),
        )
    )

    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == Decimal(3)
    assert cart.total == 30000


async def test_update_cart_reuses_existing_draft() -> None:
    user_id, customer_id, naam_id = uuid7(), uuid7(), uuid7()
    service = build(
        user_id=user_id, profiles={user_id: customer_id}, prices={naam_id: 10000}
    )
    org_unit_id = uuid7()

    first = await service.update_cart(
        UpdateCartCommand(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.PICKUP,
            lines=(CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(1)),),
        )
    )
    second = await service.update_cart(
        UpdateCartCommand(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.DELIVERY,
            lines=(CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(5)),),
        )
    )

    assert first.id == second.id
    assert service.repository.added == 1
    assert service.repository.saved == 1
    assert second.payment_method == PaymentMethod.ON_DELIVERY
    assert second.total == 50000


async def test_update_cart_rejects_item_without_price() -> None:
    user_id, customer_id = uuid7(), uuid7()
    service = build(user_id=user_id, profiles={user_id: customer_id}, prices={})

    with pytest.raises(NotSoldAtPointError):
        await service.update_cart(
            UpdateCartCommand(
                org_unit_id=uuid7(),
                fulfillment_type=FulfillmentType.PICKUP,
                lines=(CartLineCommand(nomenclature_id=uuid7(), quantity=Decimal(1)),),
            )
        )

    assert service.repository.added == 0
    assert service.transactions.commits == 0


async def test_get_cart_returns_existing_draft() -> None:
    user_id, customer_id, naam_id = uuid7(), uuid7(), uuid7()
    service = build(
        user_id=user_id, profiles={user_id: customer_id}, prices={naam_id: 10000}
    )
    org_unit_id = uuid7()
    await service.update_cart(
        UpdateCartCommand(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.PICKUP,
            lines=(CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(2)),),
        )
    )

    cart = await service.get_cart(GetCartQuery(org_unit_id=org_unit_id))

    assert cart.total == 20000


async def test_submit_cart_creates_new_order_with_number() -> None:
    user_id, customer_id, naam_id = uuid7(), uuid7(), uuid7()
    service = build(
        user_id=user_id, profiles={user_id: customer_id}, prices={naam_id: 10000}
    )
    org_unit_id = uuid7()
    cart = await service.update_cart(
        UpdateCartCommand(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.PICKUP,
            lines=(CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(2)),),
        )
    )

    order_id = await service.submit_cart(SubmitCartCommand(org_unit_id=org_unit_id))

    order = service.repository.orders[order_id]
    assert order_id == cart.id
    assert order.status is OrderStatus.NEW
    assert order.number == 1
    assert service.repository.saved == 1


async def test_submit_cart_rejects_empty_cart() -> None:
    user_id, customer_id = uuid7(), uuid7()
    service = build(user_id=user_id, profiles={user_id: customer_id})

    with pytest.raises(EmptyCartError):
        await service.submit_cart(SubmitCartCommand(org_unit_id=uuid7()))


async def test_submit_cart_reprices_lines() -> None:
    user_id, customer_id, naam_id = uuid7(), uuid7(), uuid7()
    service = build(
        user_id=user_id, profiles={user_id: customer_id}, prices={naam_id: 10000}
    )
    org_unit_id = uuid7()
    await service.update_cart(
        UpdateCartCommand(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.PICKUP,
            lines=(CartLineCommand(nomenclature_id=naam_id, quantity=Decimal(1)),),
        )
    )
    service.catalog.set_price(naam_id, 20000)

    order_id = await service.submit_cart(SubmitCartCommand(org_unit_id=org_unit_id))

    assert service.repository.orders[order_id].lines[0].unit_price == 20000


async def test_cart_requires_customer_profile() -> None:
    user_id = uuid7()
    service = build(user_id=user_id, profiles={})

    with pytest.raises(ForbiddenError):
        await service.get_cart(GetCartQuery(org_unit_id=uuid7()))

    with pytest.raises(ForbiddenError):
        await service.update_cart(
            UpdateCartCommand(
                org_unit_id=uuid7(),
                fulfillment_type=FulfillmentType.PICKUP,
                lines=(CartLineCommand(nomenclature_id=uuid7(), quantity=Decimal(1)),),
            )
        )

    with pytest.raises(ForbiddenError):
        await service.submit_cart(SubmitCartCommand(org_unit_id=uuid7()))
