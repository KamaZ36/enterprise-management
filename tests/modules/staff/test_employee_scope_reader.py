
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.sqlalchemy import (
    SQLAlchemyOrgUnitRepository,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee.sqlalchemy import (
    SQLAlchemyEmployeeReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.sqlalchemy import (
    SQLAlchemyEmployeeRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


def make_employee(org_unit_id, suffix: str) -> Employee:
    return Employee.create(
        user_id=uuid4(),
        org_unit_id=org_unit_id,
        first_name=f"Имя{suffix}",
        last_name=f"Фамилия{suffix}",
        middle_name=None,
        phone_number=None,
        position="Мясник",
        hired_at=date(2026, 1, 15),
    )


async def test_employee_reader_limits_by_workplace(
    db_session: AsyncSession, root_org_unit_id
) -> None:
    marker = uuid4().hex[:8]
    cafe = OrgUnit.create_child(
        parent_id=root_org_unit_id,
        type=OrgUnitType.CAFE,
        code=f"{TEST_PREFIX}CAFE-{marker}",
        name=f"Кафе {marker}",
    )
    await SQLAlchemyOrgUnitRepository(db_session).add(cafe)

    at_root = make_employee(root_org_unit_id, f"Root{marker}")
    at_cafe = make_employee(cafe.id, f"Cafe{marker}")
    employees = SQLAlchemyEmployeeRepository(db_session)
    await employees.add(at_root)
    await employees.add(at_cafe)
    await db_session.commit()

    try:
        reader = SQLAlchemyEmployeeReader(db_session)

        items, total = await reader.list(limit=50, offset=0, org_unit_ids=[cafe.id])
        ids = {item.id for item in items}
        assert at_cafe.id in ids
        assert at_root.id not in ids
        assert total == len(items) == 1

        items, total = await reader.list(
            limit=50, offset=0, org_unit_ids=[root_org_unit_id]
        )
        ids = {item.id for item in items}
        assert at_root.id in ids
        assert at_cafe.id not in ids

        all_items, _ = await reader.list(limit=50, offset=0)
        all_ids = {item.id for item in all_items}
        assert {at_root.id, at_cafe.id} <= all_ids

        assert await reader.get_by_id(at_cafe.id, org_unit_ids=[root_org_unit_id]) is None
        found = await reader.get_by_id(at_cafe.id, org_unit_ids=[cafe.id])
        assert found is not None
        assert found.org_unit_id == cafe.id
    finally:
        await db_session.execute(
            text("delete from staff.employees where id in (:root, :cafe)"),
            {"root": at_root.id, "cafe": at_cafe.id},
        )
        await db_session.execute(
            text(
                "delete from business.org_unit_closure"
                " where ancestor_id = :id or descendant_id = :id"
            ),
            {"id": cafe.id},
        )
        await db_session.execute(
            text("delete from business.org_units where id = :id"),
            {"id": cafe.id},
        )
        await db_session.commit()
