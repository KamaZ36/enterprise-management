from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee.sqlalchemy import (
    SQLAlchemyEmployeeReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.sqlalchemy import (
    SQLAlchemyEmployeeRepository,
)

pytestmark = pytest.mark.db


def make_employee(
    *, org_unit_id, first_name: str, last_name: str, position: str
) -> Employee:
    return Employee.create(
        user_id=uuid4(),
        org_unit_id=org_unit_id,
        first_name=first_name,
        last_name=last_name,
        middle_name=None,
        phone_number=None,
        position=position,
        hired_at=date(2026, 1, 15),
    )


async def test_words_are_matched_in_any_order(
    db_session: AsyncSession, root_org_unit_id
) -> None:
    marker = uuid4().hex[:8]
    repository = SQLAlchemyEmployeeRepository(db_session)
    reader = SQLAlchemyEmployeeReader(db_session)

    target = make_employee(
        org_unit_id=root_org_unit_id,
        first_name=f"Имя{marker}",
        last_name=f"Фамилия{marker}",
        position="Обвальщик",
    )
    other = make_employee(
        org_unit_id=root_org_unit_id,
        first_name=f"Другой{marker}",
        last_name=f"Чужой{marker}",
        position="Мясник",
    )
    await repository.add(target)
    await repository.add(other)
    await db_session.commit()

    items, total = await reader.list(
        limit=10, offset=0, search=f"Фамилия{marker} Имя{marker}"
    )
    assert total == 1
    assert [item.id for item in items] == [target.id]

    items, total = await reader.list(
        limit=10, offset=0, search=f"Имя{marker} Фамилия{marker}"
    )
    assert total == 1
    assert [item.id for item in items] == [target.id]

    _, total = await reader.list(limit=10, offset=0, search=marker)
    assert total == 2

    items, total = await reader.list(limit=10, offset=0, search=f"Обвал{marker}")
    assert total == 0

    items, total = await reader.list(
        limit=10, offset=0, search=f"Фамилия{marker} Обвальщик"
    )
    assert total == 1
    assert [item.id for item in items] == [target.id]

    _, total = await reader.list(limit=10, offset=0, search=f"несуществует{marker}")
    assert total == 0

    _, total = await reader.list(limit=10, offset=0, search=None)
    assert total >= 2
