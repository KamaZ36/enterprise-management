from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.customer.application.dto import (
    CustomerDetail,
    CustomerListItem,
)


class CustomerReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CustomerListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, customer_id: UUID) -> CustomerDetail | None:
        raise NotImplementedError
