from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.infrastructure.readers.org_unit.sqlalchemy import (
    SQLAlchemyOrgUnitReader,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.sqlalchemy import (
    SQLAlchemyOrgUnitRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def test_reader_returns_flat_items_with_parent(
    db_session: AsyncSession,
) -> None:
    await bootstrap_system()

    root_id = await db_session.scalar(
        text("select id from business.org_units where parent_id is null limit 1")
    )
    assert root_id is not None

    marker = uuid4().hex[:6]
    repository = SQLAlchemyOrgUnitRepository(db_session)
    child = OrgUnit.create_child(
        parent_id=root_id,
        type=OrgUnitType.CAFE,
        code=f"{TEST_PREFIX}{marker}",
        name=f"Кафе {marker}",
        address="ул. Ленина, 1",
        phone_number=PhoneNumber.parse("+79001112233"),
    )
    await repository.add(child)
    await db_session.commit()

    try:
        items = await SQLAlchemyOrgUnitReader(db_session).list()

        by_id = {item.id: item for item in items}
        assert child.id in by_id
        assert by_id[child.id].parent_id == root_id
        assert by_id[child.id].type is OrgUnitType.CAFE
        assert by_id[child.id].is_active is True
        assert by_id[child.id].address == "ул. Ленина, 1"
        assert by_id[child.id].phone_number == "+79001112233"
        assert by_id[child.id].code == f"{TEST_PREFIX}{marker}"
        assert not hasattr(by_id[child.id], "created_at")
    finally:
        await db_session.execute(
            text("delete from business.org_units where id = :id"), {"id": child.id}
        )
        await db_session.commit()
