from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.customer.application.interactors.ensure_customer_profile import (
    EnsureCustomerProfileInteractor,
)
from myasnaya_derevnya.modules.customer.domain.entities.customer import (
    Customer,
    CustomerStatus,
)
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.sqlalchemy import (
    SQLAlchemyCustomerRepository,
)

pytestmark = pytest.mark.db


async def test_add_and_get_by_user_id(db_session: AsyncSession) -> None:
    repository = SQLAlchemyCustomerRepository(db_session)
    user_id = uuid4()

    await repository.add(Customer.create(user_id=user_id, first_name="Данил"))
    await db_session.commit()

    found = await repository.get_by_user_id(user_id)

    assert found is not None
    assert found.user_id == user_id
    assert found.first_name == "Данил"
    assert found.status is CustomerStatus.ACTIVE


async def test_unknown_user_returns_none(db_session: AsyncSession) -> None:
    repository = SQLAlchemyCustomerRepository(db_session)

    assert await repository.get_by_user_id(uuid4()) is None


async def test_ensure_profile_creates_once(db_session: AsyncSession) -> None:
    repository = SQLAlchemyCustomerRepository(db_session)
    interactor = EnsureCustomerProfileInteractor(customer_repository=repository)
    user_id = uuid4()

    first_id = await interactor(user_id)
    await db_session.commit()
    second_id = await interactor(user_id)
    await db_session.commit()

    assert first_id == second_id

    found = await repository.get_by_user_id(user_id)

    assert found is not None
    assert found.id == first_id
