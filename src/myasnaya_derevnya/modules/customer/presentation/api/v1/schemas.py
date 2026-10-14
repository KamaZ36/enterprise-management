from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CustomerListItemSchema(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str | None
    contact_phone: str | None
    status: str
    created_at: datetime

    @classmethod
    def from_dto(cls, item) -> CustomerListItemSchema:
        return cls(
            id=item.id,
            user_id=item.user_id,
            first_name=item.first_name,
            contact_phone=item.contact_phone,
            status=item.status,
            created_at=item.created_at,
        )


class CustomerListSchema(BaseModel):
    items: list[CustomerListItemSchema]
    total: int


class CustomerDetailSchema(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str | None
    contact_phone: str | None
    status: str
    created_at: datetime

    @classmethod
    def from_dto(cls, item) -> CustomerDetailSchema:
        return cls(
            id=item.id,
            user_id=item.user_id,
            first_name=item.first_name,
            contact_phone=item.contact_phone,
            status=item.status,
            created_at=item.created_at,
        )
