from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CustomerListItem:
    id: UUID
    user_id: UUID
    first_name: str | None
    contact_phone: str | None
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CustomerDetail:
    id: UUID
    user_id: UUID
    first_name: str | None
    contact_phone: str | None
    status: str
    created_at: datetime
