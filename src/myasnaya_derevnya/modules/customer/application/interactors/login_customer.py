import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.customer.application.errors import CustomerBlocked
from myasnaya_derevnya.modules.customer.application.interactors.ensure_customer_profile import (
    EnsureCustomerProfileInteractor,
)
from myasnaya_derevnya.modules.customer.domain.entities.customer import CustomerStatus
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.base import (
    CustomerRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RequestLoginCodeCommand:
    phone: str


@dataclass(frozen=True, slots=True)
class LoginCustomerCommand:
    phone: str
    code: str


class LoginCustomerInteractor:
    def __init__(
        self,
        auth_api: AuthAPI,
        ensure_customer_profile_interactor: EnsureCustomerProfileInteractor,
        customer_repository: CustomerRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._auth_api = auth_api
        self._ensure_customer_profile_interactor = ensure_customer_profile_interactor
        self._customer_repository = customer_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, phone: str, code: str) -> UUID:
        await self._auth_api.verify_login_code(phone, code)
        user_id = await self._auth_api.ensure_user_by_phone(phone)
        await self._ensure_customer_profile_interactor(user_id)

        customer = await self._customer_repository.get_by_user_id(user_id)

        if customer is None or customer.status is CustomerStatus.BLOCKED:
            logger.warning("Вход клиента отклонён: профиль заблокирован или отсутствует")
            raise CustomerBlocked()

        session_id = await self._auth_api.start_session(user_id)
        await self._transaction_manager.commit()

        logger.info("Вход клиента", extra={"user_id": str(user_id)})

        return session_id
