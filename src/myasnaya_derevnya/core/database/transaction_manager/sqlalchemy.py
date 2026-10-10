from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.base import (
    TransactionManager,
)
from myasnaya_derevnya.core.errors import ConflictError, UniqueViolationError

UNIQUE_VIOLATION = "23505"


def _original(exc: IntegrityError) -> object | None:
    """asyncpg прячет исходное исключение за обёрткой драйвера."""
    orig = getattr(exc, "orig", None)
    return getattr(orig, "__cause__", None) or orig


def _sqlstate(exc: IntegrityError) -> str | None:
    return getattr(_original(exc), "sqlstate", None)


def _constraint_name(exc: IntegrityError) -> str | None:
    return getattr(_original(exc), "constraint_name", None)


class SQLAlchemyTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()

            if _sqlstate(exc) == UNIQUE_VIOLATION:
                raise UniqueViolationError(constraint=_constraint_name(exc)) from exc

            raise ConflictError() from exc

    async def rollback(self) -> None:
        await self._session.rollback()
