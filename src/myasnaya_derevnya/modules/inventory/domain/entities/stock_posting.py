from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class StockPosting:
    """Событие проведения: якорь, к которому привязаны проводки.

    Документы живут в своих таблицах, поэтому общей ссылки на них нет.
    Уникальность пары (тип, документ) не даёт провести документ дважды.
    """

    id: UUID
    document_type: str
    document_id: UUID
    warehouse_id: UUID
    posted_at: datetime
    posted_by: UUID | None

    @classmethod
    def create(
        cls,
        document_type: str,
        document_id: UUID,
        warehouse_id: UUID,
        posted_by: UUID | None = None,
    ) -> StockPosting:
        return cls(
            id=uuid7(),
            document_type=document_type,
            document_id=document_id,
            warehouse_id=warehouse_id,
            posted_at=get_datetime_utc(),
            posted_by=posted_by,
        )
