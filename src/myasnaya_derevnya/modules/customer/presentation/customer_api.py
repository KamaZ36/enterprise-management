from uuid import UUID

from myasnaya_derevnya.modules.customer.application.interactors.ensure_customer_profile import (
    EnsureCustomerProfileInteractor,
)
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.base import (
    CustomerRepository,
)


class CustomerAPI:
    def __init__(
        self,
        ensure_customer_profile_interactor: EnsureCustomerProfileInteractor,
        customer_repository: CustomerRepository,
    ) -> None:
        self._ensure_customer_profile_interactor = ensure_customer_profile_interactor
        self._customer_repository = customer_repository

    async def ensure_profile(self, user_id: UUID) -> UUID:
        return await self._ensure_customer_profile_interactor(user_id)

    async def get_customer_id(self, user_id: UUID) -> UUID | None:
        customer = await self._customer_repository.get_by_user_id(user_id)

        return customer.id if customer is not None else None

    async def contact_phone_by_customer_id(self, customer_id: UUID) -> str | None:
        customer = await self._customer_repository.get_by_id(customer_id)

        return customer.contact_phone if customer is not None else None
