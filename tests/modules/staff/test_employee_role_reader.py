
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
    RoleAssignmentStatus,
)
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee_role.sqlalchemy import (
    SQLAlchemyEmployeeRoleReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.sqlalchemy import (
    SQLAlchemyRoleAssignmentRepository,
)

pytestmark = pytest.mark.db


async def test_reader_returns_active_roles_with_names(
    db_session: AsyncSession,
) -> None:
    await bootstrap_system()

    role_id = await db_session.scalar(
        text("select id from staff.roles where code = :code"),
        {"code": settings.admin_role_code},
    )
    assert role_id is not None

    user_id = uuid4()
    repository = SQLAlchemyRoleAssignmentRepository(db_session)
    assignment = RoleAssignment.create(
        user_id=user_id,
        role_id=role_id,
        org_unit_id=None,
        include_descendants=True,
        granted_by=uuid4(),
    )
    await repository.add(assignment)
    await db_session.commit()

    try:
        items = await SQLAlchemyEmployeeRoleReader(db_session).list_active_for_user(
            user_id
        )

        assert len(items) == 1
        assert items[0].id == assignment.id
        assert items[0].role_code == settings.admin_role_code
        assert items[0].role_name == settings.admin_role_name
        assert items[0].status is RoleAssignmentStatus.ACTIVE
        assert items[0].include_descendants is True
        assert not hasattr(items[0], "granted_by")

        others = await SQLAlchemyEmployeeRoleReader(db_session).list_active_for_user(
            uuid4()
        )
        assert others == []

        await db_session.execute(
            text("update staff.role_assignments set status = :status where id = :id"),
            {"status": RoleAssignmentStatus.REVOKED.value, "id": assignment.id},
        )
        await db_session.commit()

        revoked = await SQLAlchemyEmployeeRoleReader(db_session).list_active_for_user(
            user_id
        )
        assert revoked == []
    finally:
        await db_session.execute(
            text("delete from staff.role_assignments where id = :id"),
            {"id": assignment.id},
        )
        await db_session.commit()
