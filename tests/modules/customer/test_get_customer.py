from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError, NotFoundError
from myasnaya_derevnya.modules.customer.application.dto import CustomerDetail
from myasnaya_derevnya.modules.customer.application.interactors.get_customer import (
    GetCustomerInteractor,
    GetCustomerQuery,
)
from myasnaya_derevnya.modules.customer.domain.permissions import READ_CUSTOMERS
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.fakes import FakeIdentityProvider, FakeStaffAPI


class FakeCustomerReader:
    def __init__(self, detail: CustomerDetail | None) -> None:
        self.detail = detail
        self.asked: list = []

    async def get(self, customer_id):
        self.asked.append(customer_id)
        return self.detail


def build(*, allowed: bool = True):
    detail = CustomerDetail(
        id=uuid4(),
        user_id=uuid4(),
        first_name="Данил",
        contact_phone="+79991234567",
        status="active",
        created_at=get_datetime_utc(),
    )
    reader = FakeCustomerReader(detail)
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = GetCustomerInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        customer_reader=reader,
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_requires_read_permission() -> None:
    interactor, reader, _ = build(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(GetCustomerQuery(uuid4()))

    assert reader.asked == []


async def test_checks_read_customers_permission() -> None:
    interactor, _, staff_api = build()

    await interactor(GetCustomerQuery(uuid4()))

    assert staff_api.checked == [(READ_CUSTOMERS.code, None)]


async def test_unknown_customer_raises_not_found() -> None:
    interactor, reader, _ = build()
    reader.detail = None

    with pytest.raises(NotFoundError):
        await interactor(GetCustomerQuery(uuid4()))


async def test_returns_customer_detail() -> None:
    interactor, reader, _ = build()
    customer_id = uuid4()

    result = await interactor(GetCustomerQuery(customer_id))

    assert result is reader.detail
    assert reader.asked == [customer_id]
