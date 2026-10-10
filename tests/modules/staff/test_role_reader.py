"""Интеграционный тест читателя ролей на настоящем PostgreSQL."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.staff.infrastructure.readers.role.sqlalchemy import (
    SQLAlchemyRoleReader,
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
    # Плоские данные, а не доменная сущность
    assert not hasattr(role, "grantable_role_ids")
    # Порядок: сначала старшие уровни
    levels = [item.level for item in items]
    assert levels == sorted(levels, reverse=True)
