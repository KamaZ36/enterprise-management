from collections.abc import Callable, Coroutine
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
async def make_location(
    db_session: AsyncSession, root_org_unit_id: UUID
) -> Callable[..., Coroutine]:
    """Создаёт подразделение, которое хранит запасы (складскую локацию)."""

    repository = SQLAlchemyOrgUnitRepository(db_session)

    async def factory(
        type_: OrgUnitType = OrgUnitType.PRODUCTION,
        org_unit_id: UUID | None = None,
        name: str = "Локация",
        is_active: bool = True,
    ) -> OrgUnit:
        now = get_datetime_utc()
        org_unit = OrgUnit(
            id=org_unit_id or uuid4(),
            parent_id=root_org_unit_id,
            type=type_,
            code=f"{TEST_PREFIX}{uuid4().hex[:8]}",
            name=name,
            address=None,
            phone_number=None,
            timezone=None,
            is_active=is_active,
            attributes={},
            created_at=now,
            updated_at=now,
        )
        await repository.add(org_unit)
        await db_session.commit()

        return org_unit

    return factory
