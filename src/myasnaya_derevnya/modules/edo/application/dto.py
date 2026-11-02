from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EdoDocumentListItem:
    id: UUID
    org_unit_id: UUID
    external_id: str | None
    number: str
    doc_date: date | None
    supplier_name: str | None
    supplier_inn: str | None
    delivery_address: str | None
    comment: str | None
    status: str
    created_by: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EdoDocumentInfo:
    id: UUID
    org_unit_id: UUID
    number: str
