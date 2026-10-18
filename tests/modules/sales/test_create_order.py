import logging
from decimal import Decimal
from uuid import UUID, uuid7

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.sales.application.interactors.create_order import (
    CreateOrderCommand,
    CreateOrderInteractor,
    OrderLineCommand,
)
from myasnaya_derevnya.modules.sales.domain.errors import NotSoldAtPointError
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_status import (
    OrderStatus,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeStaffAPI:
    def __init__(self, allowed_users: set[UUID]) -> None:
        self._allowed = allowed_users

    async def can(
        self, *, user_id: UUID, permission: object, org_unit_id: UUID
    ) -> bool:
        return user_id in self._allowed


class FakeCustomerAPI:
    def __init__(self, profiles: dict[UUID, UUID], phone: str | None = None) -> None:
        self._profiles = profiles
        self._phone = phone

    async def get_customer_id(self, user_id: UUID) -> UUID | None:
        return self._profiles.get(user_id)

    async def contact_phone_by_customer_id(self, customer_id: UUID) -> str | None:
        return self._phone


class FakeCatalogAPI:
    def __init__(self, prices: dict[UUID, int]) -> None:
        self._prices = prices
        self.asked: list[UUID] = []

    async def prices_for_point(
        self, org_unit_id: UUID, nomenclature_ids: list[UUID]
    ) -> dict[UUID, int]:
        self.asked = list(nomenclature_ids)

        return {
            item: self._prices[item]
            for item in nomenclature_ids
            if item in self._prices
        }


class FakeOrderRepository:
    def __init__(self) -> None:
        self.saved: list[object] = []

    async def add(self, order: object) -> None:
        self.saved.append(order)

    async def next_number(self, org_unit_id: UUID, day: object) -> int:
        return 1


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def build(
    *,
    user_id: UUID,
    staff_users: set[UUID] | None = None,
    profiles: dict[UUID, UUID] | None = None,
    prices: dict[UUID, int] | None = None,
    phone: str | None = None,
) -> tuple[
    CreateOrderInteractor, FakeOrderRepository, FakeCatalogAPI, FakeTransactionManager
]:
    repository = FakeOrderRepository()
    catalog = FakeCatalogAPI(prices or {})
    transactions = FakeTransactionManager()

    interactor = CreateOrderInteractor(
        identity_provider=FakeIdentityProvider(user_id),
        order_repository=repository,  # type: ignore[arg-type]
        catalog_api=catalog,  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI(profiles or {}, phone),  # type: ignore[arg-type]
        staff_api=FakeStaffAPI(staff_users or set()),  # type: ignore[arg-type]
        transaction_manager=transactions,  # type: ignore[arg-type]
    )

    return interactor, repository, catalog, transactions


async def test_staff_creates_order_for_customer_at_any_channel() -> None:
    staff_id, customer_id, nomenclature_id = uuid7(), uuid7(), uuid7()
    interactor, repository, _, transactions = build(
        user_id=staff_id, staff_users={staff_id}, prices={nomenclature_id: 45000}
    )

    order_id = await interactor(
        CreateOrderCommand(
            org_unit_id=uuid7(),
            channel=OrderChannel.POS,
            customer_id=customer_id,
            lines=(OrderLineCommand(nomenclature_id, Decimal(2)),),
        )
    )

    assert order_id is not None
    assert len(repository.saved) == 1
    assert transactions.commits == 1
    order = repository.saved[0]
    assert order.customer_id == customer_id  # type: ignore[attr-defined]
    assert order.total == 90000  # type: ignore[attr-defined]
    assert order.status is OrderStatus.NEW  # type: ignore[attr-defined]
    assert order.number == 1  # type: ignore[attr-defined]


async def test_customer_creates_order_for_themselves_from_site() -> None:
    user_id, customer_id, nomenclature_id = uuid7(), uuid7(), uuid7()
    interactor, repository, _, _ = build(
        user_id=user_id,
        profiles={user_id: customer_id},
        prices={nomenclature_id: 10000},
    )

    await interactor(
        CreateOrderCommand(
            org_unit_id=uuid7(),
            channel=OrderChannel.SITE,
            lines=(OrderLineCommand(nomenclature_id, Decimal(1)),),
        )
    )

    assert repository.saved[0].customer_id == customer_id  # type: ignore[attr-defined]


async def test_customer_cannot_order_for_someone_else() -> None:
    user_id, nomenclature_id = uuid7(), uuid7()
    interactor, repository, _, _ = build(
        user_id=user_id, profiles={user_id: uuid7()}, prices={nomenclature_id: 10000}
    )

    with pytest.raises(ForbiddenError):
        await interactor(
            CreateOrderCommand(
                org_unit_id=uuid7(),
                channel=OrderChannel.SITE,
                customer_id=uuid7(),
                lines=(OrderLineCommand(nomenclature_id, Decimal(1)),),
            )
        )

    assert repository.saved == []


async def test_customer_cannot_use_pos_channel() -> None:
    user_id, nomenclature_id = uuid7(), uuid7()
    interactor, repository, _, _ = build(
        user_id=user_id, profiles={user_id: uuid7()}, prices={nomenclature_id: 10000}
    )

    with pytest.raises(ForbiddenError):
        await interactor(
            CreateOrderCommand(
                org_unit_id=uuid7(),
                channel=OrderChannel.POS,
                lines=(OrderLineCommand(nomenclature_id, Decimal(1)),),
            )
        )

    assert repository.saved == []


async def test_user_without_role_and_without_profile_is_rejected() -> None:
    interactor, repository, _, _ = build(user_id=uuid7())

    with pytest.raises(ForbiddenError):
        await interactor(
            CreateOrderCommand(
                org_unit_id=uuid7(),
                channel=OrderChannel.SITE,
                lines=(OrderLineCommand(uuid7(), Decimal(1)),),
            )
        )

    assert repository.saved == []


async def test_item_without_price_at_point_is_rejected() -> None:
    staff_id, nomenclature_id = uuid7(), uuid7()
    interactor, repository, catalog, transactions = build(
        user_id=staff_id, staff_users={staff_id}, prices={}
    )

    with pytest.raises(NotSoldAtPointError):
        await interactor(
            CreateOrderCommand(
                org_unit_id=uuid7(),
                channel=OrderChannel.POS,
                lines=(OrderLineCommand(nomenclature_id, Decimal(1)),),
            )
        )

    assert repository.saved == []
    assert transactions.commits == 0
    assert catalog.asked == [nomenclature_id]


async def test_contact_phone_is_copied_into_order() -> None:
    user_id, customer_id, nomenclature_id = uuid7(), uuid7(), uuid7()
    interactor, repository, _, _ = build(
        user_id=user_id,
        profiles={user_id: customer_id},
        prices={nomenclature_id: 10000},
        phone="+7 (999) 123-45-67",
    )

    await interactor(
        CreateOrderCommand(
            org_unit_id=uuid7(),
            channel=OrderChannel.SITE,
            lines=(OrderLineCommand(nomenclature_id, Decimal(1)),),
        )
    )

    assert repository.saved[0].contact_phone == "+7 (999) 123-45-67"  # type: ignore[attr-defined]


async def test_created_order_is_logged_with_business_fields(caplog) -> None:
    staff_id, nomenclature_id = uuid7(), uuid7()
    interactor, _, _, _ = build(
        user_id=staff_id, staff_users={staff_id}, prices={nomenclature_id: 10000}
    )
    org_unit_id = uuid7()

    with caplog.at_level(
        logging.INFO,
        logger="myasnaya_derevnya.modules.sales.application.interactors.create_order",
    ):
        order_id = await interactor(
            CreateOrderCommand(
                org_unit_id=org_unit_id,
                channel=OrderChannel.POS,
                lines=(OrderLineCommand(nomenclature_id, Decimal(1)),),
            )
        )

    record = caplog.records[-1]
    assert record.getMessage() == "Заказ создан"
    assert record.order_id == str(order_id)  # type: ignore[attr-defined]
    assert record.org_unit_id == str(org_unit_id)  # type: ignore[attr-defined]
