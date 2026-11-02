from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.edo.domain.errors import EmptyEdoDocumentNumberError
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class EdoDocument:
    """Входящий документ ЭДО — пока только ручная регистрация УПД."""

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
    def create(
        cls,
        *,
        org_unit_id: UUID,
        number: str,
        external_id: str | None = None,
        doc_date: date | None = None,
        supplier_name: str | None = None,
        supplier_inn: str | None = None,
        delivery_address: str | None = None,
        comment: str | None = None,
        created_by: UUID | None = None,
    ) -> EdoDocument:
        cleaned_number = number.strip()
        if not cleaned_number:
            raise EmptyEdoDocumentNumberError()

        return cls(
            id=uuid7(),
            org_unit_id=org_unit_id,
            external_id=_clean(external_id),
            number=cleaned_number,
            doc_date=doc_date,
            supplier_name=_clean(supplier_name),
            supplier_inn=_clean(supplier_inn),
            delivery_address=_clean(delivery_address),
            comment=_clean(comment),
            status="manual",
            created_by=created_by,
            created_at=get_datetime_utc(),
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
