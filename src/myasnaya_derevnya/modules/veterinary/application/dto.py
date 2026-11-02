from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VeterinaryDocumentListItem:
    id: UUID
    org_unit_id: UUID
    number: str | None
    guid: UUID | None
    batch_id: str | None
    product_item_guid: UUID | None
    source: str
    created_by: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class VeterinaryDocumentPage:
    items: list[VeterinaryDocumentListItem]
    total: int
    limit: int
    offset: int
