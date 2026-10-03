from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)


class LogoutInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        session_repository: UserSessionRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._session_repository = session_repository
        self._transaction_manager = transaction_manager

    async def __call__(self) -> None:
        current_session_id = await self._identity_provider.get_current_session_id()
        await self._session_repository.delete_by_id(current_session_id)
        await self._transaction_manager.commit()
