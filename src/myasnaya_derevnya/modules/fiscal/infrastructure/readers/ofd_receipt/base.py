from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.fiscal.application.dto import (
    OfdReceiptDetail,
    OfdReceiptListItem,
)


class OfdReceiptReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        status: str | None,
        reg_number: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        org_unit_ids: frozenset[UUID] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[OfdReceiptListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, receipt_id: UUID) -> OfdReceiptDetail | None:
        raise NotImplementedError
