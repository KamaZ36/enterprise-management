from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.sales.application.dto import OrderDetail, OrderListItem


class OrderReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_ids: list[UUID] | None = None,
        statuses: list[str] | None = None,
        day: date | None = None,
        customer_id: UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrderListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, order_id: UUID) -> OrderDetail | None:
        raise NotImplementedError
