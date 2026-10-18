import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.conflicts import conflict_error
from myasnaya_derevnya.core.database.transaction_manager.base import (
    TransactionManager,
)

logger = logging.getLogger(__name__)


class SQLAlchemyTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            error = conflict_error(exc)
            logger.warning("Конфликт при сохранении: %s", error)
            raise error from exc

    async def rollback(self) -> None:
        await self._session.rollback()
