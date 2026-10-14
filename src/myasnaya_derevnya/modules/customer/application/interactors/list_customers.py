from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError, NotFoundError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.customer.application.dto import (
    CustomerDetail,
    CustomerListItem,
)
from myasnaya_derevnya.modules.customer.domain.permissions import READ_CUSTOMERS
from myasnaya_derevnya.modules.customer.infrastructure.readers.customer.base import (
    CustomerReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListCustomersQuery:
    search: str | None = None
    status: str | None = None
    limit: int = 50
    offset: int = 0


class ListCustomersInteractor:
    """Список клиентов для персонала: право проверяется без привязки к точке.

    Профиль клиента — общий ресурс компании, как номенклатура: он не принадлежит
    конкретному кафе. Заказы же клиента смотрятся отдельно и уже по области.
    """

    def __init__(
        self,
        identity_provider: IdentityProvider,
        customer_reader: CustomerReader,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._customer_reader = customer_reader
        self._staff_api = staff_api

    async def __call__(
        self, query: ListCustomersQuery
    ) -> tuple[list[CustomerListItem], int]:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=READ_CUSTOMERS
        ):
            raise ForbiddenError()

        return await self._customer_reader.list(
            search=query.search,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )


@dataclass(frozen=True, slots=True)
class GetCustomerQuery:
    customer_id: UUID


class GetCustomerInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        customer_reader: CustomerReader,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._customer_reader = customer_reader
        self._staff_api = staff_api

    async def __call__(self, query: GetCustomerQuery) -> CustomerDetail:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=READ_CUSTOMERS
        ):
            raise ForbiddenError()

        customer = await self._customer_reader.get(query.customer_id)

        if customer is None:
            raise NotFoundError()

        return customer
