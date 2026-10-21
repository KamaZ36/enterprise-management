from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.fiscal.application.dto import (
    CashRegisterDetail,
    CashRegisterListItem,
)


class CashRegisterReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_id: UUID | None,
        at: datetime,
    ) -> list[CashRegisterListItem]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, cash_register_id: UUID) -> CashRegisterDetail | None:
        raise NotImplementedError
