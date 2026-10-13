from uuid import UUID

from myasnaya_derevnya.modules.customer.application.interactors.ensure_customer_profile import (
    EnsureCustomerProfileInteractor,
)


class CustomerAPI:
    def __init__(
        self,
        ensure_customer_profile_interactor: EnsureCustomerProfileInteractor,
    ) -> None:
        self._ensure_customer_profile_interactor = ensure_customer_profile_interactor

    async def ensure_profile(self, user_id: UUID) -> UUID:
        return await self._ensure_customer_profile_interactor(user_id)
