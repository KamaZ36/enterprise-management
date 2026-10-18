from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.customer.application.errors import CustomerBlocked
from myasnaya_derevnya.modules.customer.application.interactors.login_customer import (
    LoginCustomerInteractor,
)
from myasnaya_derevnya.modules.customer.domain.entities.customer import (
    Customer,
    CustomerStatus,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.fakes import FakeTransactionManager

PHONE = "+79991234567"
CODE = "123456"


class FakeAuthAPI:
    def __init__(self, user_id) -> None:
        self._user_id = user_id
        self.verified: list[tuple[str, str]] = []
        self.ensured: list[str] = []
        self.sessions_started: list = []
        self.session_id = uuid4()

    async def verify_login_code(self, phone: str, code: str) -> None:
        self.verified.append((phone, code))

    async def ensure_user_by_phone(self, phone: str):
        self.ensured.append(phone)
        return self._user_id

    async def start_session(self, user_id):
        self.sessions_started.append(user_id)
        return self.session_id


class FakeEnsureProfile:
    def __init__(self) -> None:
        self.called_with: list = []

    async def __call__(self, user_id):
        self.called_with.append(user_id)
        return uuid4()


class FakeCustomerRepository:
    def __init__(self, customer: Customer | None) -> None:
        self.customer = customer

    async def get_by_user_id(self, user_id):
        return self.customer


def make_customer(user_id, status: CustomerStatus) -> Customer:
    return Customer(
        id=uuid4(),
        user_id=user_id,
        first_name=None,
        contact_phone=None,
        status=status,
        created_at=get_datetime_utc(),
    )


def build(*, status: CustomerStatus | None = CustomerStatus.ACTIVE):
    user_id = uuid4()
    auth_api = FakeAuthAPI(user_id)
    ensure_profile = FakeEnsureProfile()
    customer = make_customer(user_id, status) if status is not None else None
    transactions = FakeTransactionManager()
    interactor = LoginCustomerInteractor(
        auth_api=auth_api,
        ensure_customer_profile_interactor=ensure_profile,
        customer_repository=FakeCustomerRepository(customer),
        transaction_manager=transactions,
    )

    return interactor, auth_api, ensure_profile, transactions


async def test_verifies_code_and_creates_session() -> None:
    interactor, auth_api, ensure_profile, transactions = build()

    session_id = await interactor(PHONE, CODE)

    assert auth_api.verified == [(PHONE, CODE)]
    assert auth_api.ensured == [PHONE]
    assert ensure_profile.called_with == [auth_api._user_id]
    assert auth_api.sessions_started == [auth_api._user_id]
    assert transactions.commits == 1
    assert session_id == auth_api.session_id


async def test_blocked_customer_cannot_log_in() -> None:
    interactor, auth_api, _, transactions = build(status=CustomerStatus.BLOCKED)

    with pytest.raises(CustomerBlocked):
        await interactor(PHONE, CODE)

    assert auth_api.sessions_started == []
    assert transactions.commits == 0


async def test_missing_profile_cannot_log_in() -> None:
    interactor, auth_api, _, transactions = build(status=None)

    with pytest.raises(CustomerBlocked):
        await interactor(PHONE, CODE)

    assert auth_api.sessions_started == []
    assert transactions.commits == 0
