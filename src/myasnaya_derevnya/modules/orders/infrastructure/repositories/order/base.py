from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.orders.domain.entities.order import Order


class OrderRepository(ABC):
    @abstractmethod
    async def add(self, order: Order) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, order: Order) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> Order | None:
        raise NotImplementedError

    @abstractmethod
    async def get_open_draft(
        self, customer_id: UUID, org_unit_id: UUID
    ) -> Order | None:
        raise NotImplementedError

    @abstractmethod
    async def next_number(self, org_unit_id: UUID, day: date) -> int:
        raise NotImplementedError
