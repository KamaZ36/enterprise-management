from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.sqlalchemy import (
    SQLAlchemyOrgUnitRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.helpers import TEST_PREFIX


@pytest.fixture
async def warehouse(db_session, root_org_unit_id):
    repository = SQLAlchemyOrgUnitRepository(db_session)
    now = get_datetime_utc()
    org_unit = OrgUnit(
        id=uuid4(),
        parent_id=root_org_unit_id,
        type=OrgUnitType.PRODUCTION,
        code=f"{TEST_PREFIX}{uuid4().hex[:8]}",
        name="Склад DoKa",
        address=None,
        phone_number=None,
        timezone=None,
        is_active=True,
        attributes={},
        created_at=now,
        updated_at=now,
    )
    await repository.add(org_unit)
    await db_session.commit()
    return org_unit


