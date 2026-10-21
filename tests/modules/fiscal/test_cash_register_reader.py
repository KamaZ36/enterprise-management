from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.sqlalchemy import (
    SQLAlchemyOrgUnitRepository,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register_binding import (
    CashRegisterBinding,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.sqlalchemy import (
    SQLAlchemyCashRegisterReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.sqlalchemy import (
    SQLAlchemyCashRegisterRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
JANUARY = datetime(2026, 1, 15, tzinfo=UTC)
FEBRUARY = datetime(2026, 2, 15, tzinfo=UTC)


def make_reg_number() -> str:
    return f"{uuid4().int % 10**16:016d}"


async def create_shop(
    repository: SQLAlchemyOrgUnitRepository,
    root_org_unit_id,
    title: str,
) -> OrgUnit:
    shop = OrgUnit.create_child(
        parent_id=root_org_unit_id,
        type=OrgUnitType.SHOP,
        code=f"{TEST_PREFIX}{uuid4().hex[:8]}",
        name=f"{TEST_PREFIX}{title}",
    )
    await repository.add(shop)
    return shop


async def test_reader_returns_current_binding(
    db_session: AsyncSession, root_org_unit_id
) -> None:
    units = SQLAlchemyOrgUnitRepository(db_session)
    shop = await create_shop(units, root_org_unit_id, "Магазин 1")

    registers = SQLAlchemyCashRegisterRepository(db_session)
    register = CashRegister.create(
        name=f"{TEST_PREFIX}Касса 1", reg_number=RegNumber.parse(make_reg_number())
    )
    await registers.add(register)
    await registers.add_binding(
        CashRegisterBinding.create(
            cash_register_id=register.id,
            org_unit_id=shop.id,
            effective_from=START,
        )
    )
    await db_session.commit()

    items = await SQLAlchemyCashRegisterReader(db_session).list(
        org_unit_id=None, at=JANUARY
    )

    item = next(item for item in items if item.id == register.id)
    assert item.org_unit_id == shop.id
    assert item.reg_number == str(register.reg_number)
    assert item.name == register.name


async def test_reader_returns_register_without_binding(
    db_session: AsyncSession,
) -> None:
    registers = SQLAlchemyCashRegisterRepository(db_session)
    register = CashRegister.create(
        name=f"{TEST_PREFIX}Касса без точки", reg_number=RegNumber.parse(make_reg_number())
    )
    await registers.add(register)
    await db_session.commit()

    items = await SQLAlchemyCashRegisterReader(db_session).list(
        org_unit_id=None, at=JANUARY
    )

    item = next(item for item in items if item.id == register.id)
    assert item.org_unit_id is None


async def test_reader_filters_by_org_unit(
    db_session: AsyncSession, root_org_unit_id
) -> None:
    units = SQLAlchemyOrgUnitRepository(db_session)
    first_shop = await create_shop(units, root_org_unit_id, "Магазин 1")
    second_shop = await create_shop(units, root_org_unit_id, "Магазин 2")

    registers = SQLAlchemyCashRegisterRepository(db_session)
    first_register = CashRegister.create(
        name=f"{TEST_PREFIX}Касса 1", reg_number=RegNumber.parse(make_reg_number())
    )
    second_register = CashRegister.create(
        name=f"{TEST_PREFIX}Касса 2", reg_number=RegNumber.parse(make_reg_number())
    )
    await registers.add(first_register)
    await registers.add(second_register)
    await registers.add_binding(
        CashRegisterBinding.create(
            cash_register_id=first_register.id,
            org_unit_id=first_shop.id,
            effective_from=START,
        )
    )
    await registers.add_binding(
        CashRegisterBinding.create(
            cash_register_id=second_register.id,
            org_unit_id=second_shop.id,
            effective_from=START,
        )
    )
    await db_session.commit()

    items = await SQLAlchemyCashRegisterReader(db_session).list(
        org_unit_id=first_shop.id, at=JANUARY
    )
    ids = {item.id for item in items}

    assert first_register.id in ids
    assert second_register.id not in ids


async def test_reader_uses_binding_period(
    db_session: AsyncSession, root_org_unit_id
) -> None:
    units = SQLAlchemyOrgUnitRepository(db_session)
    first_shop = await create_shop(units, root_org_unit_id, "Магазин 1")
    second_shop = await create_shop(units, root_org_unit_id, "Магазин 2")

    registers = SQLAlchemyCashRegisterRepository(db_session)
    register = CashRegister.create(
        name=f"{TEST_PREFIX}Касса", reg_number=RegNumber.parse(make_reg_number())
    )
    await registers.add(register)

    first_binding = CashRegisterBinding.create(
        cash_register_id=register.id,
        org_unit_id=first_shop.id,
        effective_from=START,
    )
    first_binding.close(LATER)
    await registers.add_binding(first_binding)
    await registers.add_binding(
        CashRegisterBinding.create(
            cash_register_id=register.id,
            org_unit_id=second_shop.id,
            effective_from=LATER,
        )
    )
    await db_session.commit()

    reader = SQLAlchemyCashRegisterReader(db_session)

    january_items = await reader.list(org_unit_id=None, at=JANUARY)
    january = next(item for item in january_items if item.id == register.id)
    assert january.org_unit_id == first_shop.id

    february_items = await reader.list(org_unit_id=None, at=FEBRUARY)
    february = next(item for item in february_items if item.id == register.id)
    assert february.org_unit_id == second_shop.id


async def test_reader_detail_returns_binding_history(
    db_session: AsyncSession, root_org_unit_id
) -> None:
    units = SQLAlchemyOrgUnitRepository(db_session)
    first_shop = await create_shop(units, root_org_unit_id, "Магазин 1")
    second_shop = await create_shop(units, root_org_unit_id, "Магазин 2")

    registers = SQLAlchemyCashRegisterRepository(db_session)
    register = CashRegister.create(
        name=f"{TEST_PREFIX}Касса", reg_number=RegNumber.parse(make_reg_number())
    )
    await registers.add(register)

    first_binding = CashRegisterBinding.create(
        cash_register_id=register.id,
        org_unit_id=first_shop.id,
        effective_from=START,
    )
    first_binding.close(LATER)
    await registers.add_binding(first_binding)
    await registers.add_binding(
        CashRegisterBinding.create(
            cash_register_id=register.id,
            org_unit_id=second_shop.id,
            effective_from=LATER,
        )
    )
    await db_session.commit()

    detail = await SQLAlchemyCashRegisterReader(db_session).get(register.id)

    assert detail is not None
    assert len(detail.bindings) == 2
    assert detail.bindings[0].org_unit_id == second_shop.id
    assert detail.bindings[1].org_unit_id == first_shop.id
