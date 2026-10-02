from collections.abc import AsyncGenerator

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.connection import async_session_maker
from myasnaya_derevnya.core.database.transaction_manager.base import (
    TransactionManager,
)
from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)


class DatabaseProvider(Provider):
    # POSTGRESQL

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        async with async_session_maker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    async def get_transaction_manager(
        self, session: AsyncSession
    ) -> TransactionManager:
        return SQLAlchemyTransactionManager(session)

    # HTTP

    @provide(scope=Scope.APP)
    def get_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient()
