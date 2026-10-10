import pytest
from sqlalchemy.exc import IntegrityError

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.core.errors import ConflictError, UniqueViolationError


class FakeDriverError(Exception):
    def __init__(
        self, *, sqlstate: str | None = None, constraint_name: str | None = None
    ) -> None:
        super().__init__("driver error")
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class FakeSession:
    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True
        if self._exc is not None:
            raise self._exc

    async def rollback(self) -> None:
        self.rolled_back = True


def integrity_error(orig: Exception) -> IntegrityError:
    return IntegrityError("INSERT INTO t VALUES (...)", {}, orig)


async def test_commit_success_does_not_rollback() -> None:
    session = FakeSession()
    manager = SQLAlchemyTransactionManager(session)

    await manager.commit()

    assert session.committed is True
    assert session.rolled_back is False


async def test_unique_violation_becomes_conflict_with_constraint_name() -> None:
    session = FakeSession(
        integrity_error(
            FakeDriverError(sqlstate="23505", constraint_name="uq_nomenclatures_sku")
        )
    )
    manager = SQLAlchemyTransactionManager(session)

    with pytest.raises(UniqueViolationError) as error:
        await manager.commit()

    assert error.value.constraint == "uq_nomenclatures_sku"
    assert session.rolled_back is True


async def test_constraint_name_is_read_from_wrapped_driver_error() -> None:
    """asyncpg-исключение бывает завёрнуто драйвером SQLAlchemy."""
    driver_error = FakeDriverError(sqlstate="23505", constraint_name="uq_users_login")
    wrapper = FakeDriverError()
    wrapper.__cause__ = driver_error

    session = FakeSession(integrity_error(wrapper))
    manager = SQLAlchemyTransactionManager(session)

    with pytest.raises(UniqueViolationError) as error:
        await manager.commit()

    assert error.value.constraint == "uq_users_login"


async def test_non_unique_integrity_error_becomes_conflict() -> None:
    session = FakeSession(integrity_error(FakeDriverError(sqlstate="23503")))
    manager = SQLAlchemyTransactionManager(session)

    with pytest.raises(ConflictError) as error:
        await manager.commit()

    assert not isinstance(error.value, UniqueViolationError)
    assert session.rolled_back is True


async def test_rollback_is_explicit() -> None:
    session = FakeSession()
    manager = SQLAlchemyTransactionManager(session)

    await manager.rollback()

    assert session.rolled_back is True
