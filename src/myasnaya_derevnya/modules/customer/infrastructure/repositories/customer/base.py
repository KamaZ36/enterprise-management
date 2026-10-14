from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.customer.domain.entities.customer import Customer


class CustomerRepository(ABC):
    @abstractmethod
    async def add(self, customer: Customer) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Customer | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        raise NotImplementedError
