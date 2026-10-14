from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.sales.application.dto import (
    OrderDetail,
    OrderLineItem,
    OrderListItem,
)
from myasnaya_derevnya.modules.sales.application.interactors.get_my_order import (
    GetMyOrderInteractor,
    GetMyOrderQuery,
)
from myasnaya_derevnya.modules.sales.application.interactors.get_order import (
    GetOrderInteractor,
    GetOrderQuery,
)
from myasnaya_derevnya.modules.sales.application.interactors.list_my_orders import (
    ListMyOrdersInteractor,
    ListMyOrdersQuery,
)
from myasnaya_derevnya.modules.sales.application.interactors.list_orders import (
    ListOrdersInteractor,
    ListOrdersQuery,
)
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.domain.errors import OrderNotFoundError
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeStaffAPI:
    def __init__(
        self,
        allowed: set[UUID],
        scopes: list[tuple[UUID | None, bool]] | None = None,
        descendants: set[UUID] | None = None,
    ) -> None:
        self._allowed = allowed
        self._descendants = descendants or set()
        self._scopes = (
            scopes if scopes is not None else ([(None, False)] if allowed else [])
        )

    async def can(
        self, *, user_id: UUID, permission: object, org_unit_id: UUID
    ) -> bool:
        return user_id in self._allowed

    async def scope_for(self, *, user_id: UUID, permission: object) -> AccessScope:
        if user_id not in self._allowed:
            return AccessScope.of([])

        if not self._scopes:
            return AccessScope.of([])

        if any(org_unit_id is None for org_unit_id, _ in self._scopes):
            return AccessScope.company_wide()

        units: set[UUID] = set()
        for org_unit_id, descendants in self._scopes:
            if org_unit_id is None:
                continue
            units.add(org_unit_id)
            if descendants:
                units.add(org_unit_id)

        return AccessScope.of(units | self._descendants)
        return self._scopes if user_id in self._allowed else []


class FakeCustomerAPI:
    def __init__(self, profiles: dict[UUID, UUID]) -> None:
        self._profiles = profiles

    async def get_customer_id(self, user_id: UUID) -> UUID | None:
        return self._profiles.get(user_id)


class FakeBusinessAPI:
    def __init__(self, descendants: set[UUID] | None = None) -> None:
        self._descendants = descendants or set()

    async def get_root_unit_id(self) -> UUID:
        return UUID(int=1)

    async def org_unit_descendants_of(self, org_unit_ids: object) -> frozenset[UUID]:
        return frozenset(self._descendants) | frozenset(org_unit_ids)


class FakeCatalogAPI:
    async def nomenclature_names(self, nomenclature_ids: object) -> dict[UUID, str]:
        return {
            nomenclature_id: "Говядина лопатка" for nomenclature_id in nomenclature_ids
        }


class FakeOrderReader:
    def __init__(self, detail: OrderDetail | None = None) -> None:
        self.last_kwargs: dict[str, object] = {}
        self._detail = detail

    async def list(self, **kwargs: object) -> tuple[list[OrderListItem], int]:
        self.last_kwargs = kwargs

        return [], 0

    async def get(self, order_id: UUID) -> OrderDetail | None:
        return self._detail


def make_detail(customer_id: UUID | None) -> OrderDetail:
    return OrderDetail(
        id=uuid7(),
        number=1,
        status="draft",
        channel="site",
        org_unit_id=uuid7(),
        customer_id=customer_id,
        created_by=uuid7(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        planned_at=None,
        comment=None,
        contact_phone=None,
        completed_at=None,
        cancelled_at=None,
        total=15000,
        lines=[
            OrderLineItem(
                nomenclature_id=uuid7(),
                nomenclature_name=None,
                quantity=Decimal("1.5"),
                unit_price=10000,
                total=15000,
            )
        ],
    )


def build(
    user_id: UUID,
    *,
    staff: set[UUID] | None = None,
    scopes: list[tuple[UUID | None, bool]] | None = None,
    profiles: dict[UUID, UUID] | None = None,
    detail: OrderDetail | None = None,
    descendants: set[UUID] | None = None,
):
    staff_api = FakeStaffAPI(staff or set(), scopes, descendants)
    access = OrderAccess(
        staff_api=staff_api,  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI(profiles or {}),  # type: ignore[arg-type]
    )
    reader = FakeOrderReader(detail)

    return (
        ListOrdersInteractor(
            identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
            order_reader=reader,  # type: ignore[arg-type]
            order_access=access,
            staff_api=staff_api,  # type: ignore[arg-type]
        ),
        GetOrderInteractor(
            identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
            order_reader=reader,  # type: ignore[arg-type]
            order_access=access,
            catalog_api=FakeCatalogAPI(),  # type: ignore[arg-type]
        ),
        reader,
    )


async def test_staff_sees_all_orders() -> None:
    staff_id = uuid7()
    listing, _, reader = build(user_id=staff_id, staff={staff_id})

    await listing(ListOrdersQuery(limit=10))

    assert reader.last_kwargs["customer_id"] is None


async def test_customer_cannot_use_staff_list() -> None:
    user_id, customer_id = uuid7(), uuid7()
    listing, _, reader = build(user_id=user_id, profiles={user_id: customer_id})

    with pytest.raises(ForbiddenError):
        await listing(ListOrdersQuery(limit=10))

    assert reader.last_kwargs == {}


async def test_unknown_user_cannot_list_orders() -> None:
    listing, _, reader = build(user_id=uuid7())

    with pytest.raises(ForbiddenError):
        await listing(ListOrdersQuery())

    assert reader.last_kwargs == {}


async def test_customer_cannot_open_someone_elses_order() -> None:
    user_id = uuid7()
    _, getting, _ = build(
        user_id=user_id,
        profiles={user_id: uuid7()},
        detail=make_detail(customer_id=uuid7()),
    )

    with pytest.raises(ForbiddenError):
        await getting(GetOrderQuery(order_id=uuid7()))


async def test_owner_opens_own_order_and_sees_names() -> None:
    user_id, customer_id = uuid7(), uuid7()
    detail = make_detail(customer_id=customer_id)
    _, getting, _ = build(
        user_id=user_id, profiles={user_id: customer_id}, detail=detail
    )

    result = await getting(GetOrderQuery(order_id=detail.id))

    assert result.lines[0].nomenclature_name == "Говядина лопатка"
    assert result.total == 15000


async def test_unknown_order_is_reported() -> None:
    staff_id = uuid7()
    _, getting, _ = build(user_id=staff_id, staff={staff_id})

    with pytest.raises(OrderNotFoundError):
        await getting(GetOrderQuery(order_id=uuid7()))


async def test_manager_sees_only_their_point() -> None:
    staff_id, point = uuid7(), uuid7()
    listing, _, reader = build(
        user_id=staff_id, staff={staff_id}, scopes=[(point, False)]
    )

    await listing(ListOrdersQuery(limit=10))

    assert reader.last_kwargs["org_unit_ids"] == [point]
    assert reader.last_kwargs["customer_id"] is None


async def test_director_scope_expands_to_descendants() -> None:
    staff_id, group = uuid7(), uuid7()
    child_a, child_b = uuid7(), uuid7()
    listing, _, reader = build(
        user_id=staff_id,
        staff={staff_id},
        scopes=[(group, True)],
        descendants={group, child_a, child_b},
    )

    await listing(ListOrdersQuery(limit=10))

    assert set(reader.last_kwargs["org_unit_ids"]) == {group, child_a, child_b}


async def test_requested_point_narrows_scope() -> None:
    staff_id, group, child_a, other = uuid7(), uuid7(), uuid7(), uuid7()
    listing, _, reader = build(
        user_id=staff_id,
        staff={staff_id},
        scopes=[(group, True)],
        descendants={group, child_a},
    )

    await listing(ListOrdersQuery(org_unit_id=child_a, limit=10))
    assert reader.last_kwargs["org_unit_ids"] == [child_a]

    with pytest.raises(ForbiddenError):
        await listing(ListOrdersQuery(org_unit_id=other, limit=10))


async def test_wildcard_scope_is_company_wide() -> None:
    staff_id = uuid7()
    listing, _, reader = build(
        user_id=staff_id, staff={staff_id}, scopes=[(None, False)]
    )

    await listing(ListOrdersQuery(limit=10))

    assert reader.last_kwargs["org_unit_ids"] is None


async def test_my_orders_are_filtered_by_own_profile() -> None:
    user_id, customer_id = uuid7(), uuid7()
    reader = FakeOrderReader()

    interactor = ListMyOrdersInteractor(
        identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
        order_reader=reader,  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI({user_id: customer_id}),  # type: ignore[arg-type]
    )

    await interactor(ListMyOrdersQuery(limit=10))

    assert reader.last_kwargs["customer_id"] == customer_id
    assert "org_unit_ids" not in reader.last_kwargs


async def test_my_orders_require_customer_profile() -> None:
    user_id = uuid7()
    reader = FakeOrderReader()

    interactor = ListMyOrdersInteractor(
        identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
        order_reader=reader,  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI({}),  # type: ignore[arg-type]
    )

    with pytest.raises(ForbiddenError):
        await interactor(ListMyOrdersQuery())

    assert reader.last_kwargs == {}


async def test_another_customers_order_is_reported_as_not_found() -> None:
    user_id, customer_id = uuid7(), uuid7()
    order = make_detail(customer_id=uuid7())

    interactor = GetMyOrderInteractor(
        identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
        order_reader=FakeOrderReader(order),  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI({user_id: customer_id}),  # type: ignore[arg-type]
        catalog_api=FakeCatalogAPI(),  # type: ignore[arg-type]
    )


    with pytest.raises(OrderNotFoundError):
        await interactor(GetMyOrderQuery(order_id=order.id))


async def test_own_order_is_returned_with_names() -> None:
    user_id, customer_id = uuid7(), uuid7()
    order = make_detail(customer_id=customer_id)

    interactor = GetMyOrderInteractor(
        identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
        order_reader=FakeOrderReader(order),  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI({user_id: customer_id}),  # type: ignore[arg-type]
        catalog_api=FakeCatalogAPI(),  # type: ignore[arg-type]
    )

    result = await interactor(GetMyOrderQuery(order_id=order.id))

    assert result.lines[0].nomenclature_name == "Говядина лопатка"
