from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.edo.application.dto import EdoDocumentListItem


class CreateEdoDocumentSchema(BaseModel):
    org_unit_id: UUID
    number: str = Field(min_length=1, max_length=64)
    external_id: str | None = Field(default=None, max_length=128)
    doc_date: date | None = None
    supplier_name: str | None = Field(default=None, max_length=255)
    supplier_inn: str | None = Field(default=None, max_length=12)
    delivery_address: str | None = Field(default=None, max_length=512)
    comment: str | None = Field(default=None, max_length=512)


class EdoDocumentSchema(BaseModel):
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

    @classmethod
    def from_dto(cls, item: EdoDocumentListItem) -> EdoDocumentSchema:
        return cls(
            id=item.id,
            org_unit_id=item.org_unit_id,
            external_id=item.external_id,
            number=item.number,
            doc_date=item.doc_date,
            supplier_name=item.supplier_name,
            supplier_inn=item.supplier_inn,
            delivery_address=item.delivery_address,
            comment=item.comment,
            status=item.status,
            created_by=item.created_by,
            created_at=item.created_at,
        )


class EdoDocumentListSchema(BaseModel):
    items: list[EdoDocumentSchema]
    total: int
    limit: int
    offset: int
