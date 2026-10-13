from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.one_time_code import OneTimeCode
from myasnaya_derevnya.modules.auth.infrastructure.repositories.one_time_code.sqlalchemy import (
    SQLAlchemyOneTimeCodeRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc

pytestmark = pytest.mark.db


def make_code(
    *, identifier: str, code_hash: str = "hash", ttl_minutes: int = 5
) -> OneTimeCode:
    return OneTimeCode.create(
        identifier=identifier,
        code_hash=code_hash,
        ttl=timedelta(minutes=ttl_minutes),
        max_attempts=3,
    )


async def test_add_and_get_latest(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOneTimeCodeRepository(db_session)
    identifier = f"+7999{uuid4().int % 10**7:07d}"

    await repository.add(make_code(identifier=identifier, code_hash="первый"))
    await repository.add(make_code(identifier=identifier, code_hash="второй"))
    await db_session.commit()

    latest = await repository.get_latest_by_identifier(identifier)

    assert latest is not None
    assert latest.identifier == identifier
    assert latest.code_hash == "второй"
    assert latest.attempts == 0
    assert latest.max_attempts == 3
    assert latest.expires_at > get_datetime_utc()


async def test_unknown_identifier_returns_none(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOneTimeCodeRepository(db_session)

    assert await repository.get_latest_by_identifier("+70000000000") is None


async def test_update_attempts_and_delete(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOneTimeCodeRepository(db_session)
    identifier = f"+7999{uuid4().int % 10**7:07d}"

    await repository.add(make_code(identifier=identifier))
    await db_session.commit()

    code = await repository.get_latest_by_identifier(identifier)
    assert code is not None

    code.register_failed_attempt()
    code.register_failed_attempt()
    await repository.update(code)
    await db_session.commit()

    reloaded = await repository.get_latest_by_identifier(identifier)
    assert reloaded is not None
    assert reloaded.attempts == 2

    await repository.delete_by_identifier(identifier)
    await db_session.commit()

    assert await repository.get_latest_by_identifier(identifier) is None


async def test_count_created_since_filters_by_time(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOneTimeCodeRepository(db_session)
    identifier = f"+7999{uuid4().int % 10**7:07d}"

    await repository.add(make_code(identifier=identifier))
    await db_session.commit()

    assert (
        await repository.count_created_since(
            identifier, get_datetime_utc() - timedelta(hours=1)
        )
        == 1
    )
    assert (
        await repository.count_created_since(
            identifier, get_datetime_utc() + timedelta(minutes=1)
        )
        == 0
    )
