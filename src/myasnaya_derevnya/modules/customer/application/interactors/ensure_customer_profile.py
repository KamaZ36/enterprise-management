from uuid import UUID

from myasnaya_derevnya.modules.customer.domain.entities.customer import Customer
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.base import (
    CustomerRepository,
)


class EnsureCustomerProfileInteractor:
    def __init__(self, customer_repository: CustomerRepository) -> None:
        self._customer_repository = customer_repository

    async def __call__(self, user_id: UUID) -> UUID:
        customer = await self._customer_repository.get_by_user_id(user_id)

        if customer is not None:
            return customer.id

        customer = Customer.create(user_id=user_id)
        await self._customer_repository.add(customer)

        return customer.id
