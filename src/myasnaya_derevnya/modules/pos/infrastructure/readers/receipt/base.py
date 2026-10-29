from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.pos.application.dto import (
    PosReceiptDetail,
    PosReceiptListItem,
)


class PosReceiptReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        source_id: UUID | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        org_unit_ids: frozenset[UUID] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[PosReceiptListItem], int]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, receipt_id: UUID) -> PosReceiptDetail | None:
        raise NotImplementedError
