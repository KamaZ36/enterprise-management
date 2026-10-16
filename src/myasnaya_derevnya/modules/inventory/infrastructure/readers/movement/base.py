from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import MovementListItem


class MovementReader(ABC):
    @abstractmethod
    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        nomenclature_id: UUID | None = None,
        movement_types: Sequence[str] = (),
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MovementListItem], int]:
        raise NotImplementedError
