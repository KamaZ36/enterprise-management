from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.infrastructure.readers.role.sqlalchemy import (
    SQLAlchemyRoleReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.sqlalchemy import (
    SQLAlchemyRoleRepository,
)

pytestmark = pytest.mark.db


async def test_reader_returns_seeded_role_ordered_by_level(
    db_session: AsyncSession,
) -> None:
    await bootstrap_system()

    items = await SQLAlchemyRoleReader(db_session).list()

    by_code = {item.code: item for item in items}
    assert settings.admin_role_code in by_code

    role = by_code[settings.admin_role_code]
    assert role.name == settings.admin_role_name
    assert role.is_wildcard is True
    assert not hasattr(role, "grantable_role_ids")
    levels = [item.level for item in items]
    assert levels == sorted(levels, reverse=True)


async def test_reader_aggregates_permission_codes(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    repository = SQLAlchemyRoleRepository(db_session)
    with_permissions = Role.create(
        code=f"PYTEST-{marker}-WITH-PERMISSIONS",
        name="Кладовщик",
        description=None,
        level=10,
        is_system=False,
        is_assignable=True,
        is_wildcard=False,
        permission_codes=frozenset({"nomenclature.read", "inventory.balance.read"}),
        grantable_role_ids=frozenset(),
    )
    without_permissions = Role.create(
        code=f"PYTEST-{marker}-WITHOUT-PERMISSIONS",
        name="Без прав",
        description=None,
        level=5,
        is_system=False,
        is_assignable=True,
        is_wildcard=False,
        permission_codes=frozenset(),
        grantable_role_ids=frozenset(),
    )
    await repository.add(with_permissions)
    await repository.add(without_permissions)
    await db_session.commit()

    try:
        items = await SQLAlchemyRoleReader(db_session).list()
        by_code = {item.code: item for item in items}

        assert by_code[
            f"PYTEST-{marker}-WITH-PERMISSIONS"
        ].permission_codes == frozenset({"nomenclature.read", "inventory.balance.read"})
        assert (
            by_code[f"PYTEST-{marker}-WITHOUT-PERMISSIONS"].permission_codes
            == frozenset()
        )
    finally:
        await db_session.execute(
            text("delete from staff.roles where code like 'PYTEST-%'")
        )
        await db_session.commit()
