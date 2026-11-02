from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.veterinary.application.dto import (
    VeterinaryDocumentListItem,
)


class VeterinaryDocumentSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    number: str | None
    guid: UUID | None
    batch_id: str | None
    product_item_guid: UUID | None
    source: str
    created_by: UUID | None
    created_at: datetime

    @classmethod
    def from_dto(cls, item: VeterinaryDocumentListItem) -> VeterinaryDocumentSchema:
        return cls(
            id=item.id,
            org_unit_id=item.org_unit_id,
            number=item.number,
            guid=item.guid,
            batch_id=item.batch_id,
            product_item_guid=item.product_item_guid,
            source=item.source,
            created_by=item.created_by,
            created_at=item.created_at,
        )


class VeterinaryDocumentListSchema(BaseModel):
    items: list[VeterinaryDocumentSchema]
    total: int
    limit: int
    offset: int
