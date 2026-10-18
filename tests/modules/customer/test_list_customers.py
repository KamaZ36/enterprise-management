from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.customer.application.dto import CustomerListItem
from myasnaya_derevnya.modules.customer.application.interactors.list_customers import (
    ListCustomersInteractor,
    ListCustomersQuery,
)
from myasnaya_derevnya.modules.customer.domain.permissions import READ_CUSTOMERS
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.fakes import FakeIdentityProvider, FakeStaffAPI


class FakeCustomerReader:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.items: list[CustomerListItem] = []
        self.total = 0

    async def list(self, *, search, status, limit, offset):
        self.calls.append(
            {"search": search, "status": status, "limit": limit, "offset": offset}
        )

        return self.items, self.total


def build(*, allowed: bool = True):
    reader = FakeCustomerReader()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = ListCustomersInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        customer_reader=reader,
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_requires_read_permission() -> None:
    interactor, reader, _ = build(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListCustomersQuery())

    assert reader.calls == []


async def test_checks_read_customers_permission() -> None:
    interactor, _, staff_api = build()

    await interactor(ListCustomersQuery())

    assert staff_api.checked == [(READ_CUSTOMERS.code, None)]


async def test_passes_filters_and_returns_page() -> None:
    interactor, reader, _ = build()
    item = CustomerListItem(
        id=uuid4(),
        user_id=uuid4(),
        first_name="Данил",
        contact_phone="+79991234567",
        status="active",
        created_at=get_datetime_utc(),
    )
    reader.items = [item]
    reader.total = 1

    items, total = await interactor(
        ListCustomersQuery(search="Дан", status="active", limit=10, offset=5)
    )

    assert reader.calls == [
        {"search": "Дан", "status": "active", "limit": 10, "offset": 5}
    ]
    assert items == [item]
    assert total == 1


async def test_defaults_are_forwarded_unchanged() -> None:
    interactor, reader, _ = build()

    await interactor(ListCustomersQuery())

    assert reader.calls == [
        {"search": None, "status": None, "limit": 50, "offset": 0}
    ]
