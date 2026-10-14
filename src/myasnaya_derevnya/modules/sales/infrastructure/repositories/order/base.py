from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.sales.domain.entities.order import Order


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
    async def next_number(self, org_unit_id: UUID, day: date) -> int:
        """Следующий номер заказа для точки и дня: повар выкрикивает номер, не идентификатор."""
        raise NotImplementedError
