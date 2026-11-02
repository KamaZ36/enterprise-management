from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.veterinary.domain.errors import (
    EmptyVeterinaryDocumentError,
)
from myasnaya_derevnya.utils import get_datetime_utc


class VeterinaryDocumentSource(StrEnum):
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class VeterinaryDocument:
    """Ветеринарный сопроводительный документ.

    Пока поддерживается только ручной ввод. Источник хранится отдельно,
    чтобы позже добавить загрузку из ВетИС.API без изменения модели.
    """

    id: UUID
    org_unit_id: UUID
    number: str | None
    guid: UUID | None
    batch_id: str | None
    product_item_guid: UUID | None
    source: VeterinaryDocumentSource
    created_by: UUID | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        org_unit_id: UUID,
        number: str | None = None,
        guid: UUID | None = None,
        batch_id: str | None = None,
        product_item_guid: UUID | None = None,
        created_by: UUID | None = None,
    ) -> VeterinaryDocument:
        number = number.strip() if number else None
        batch_id = batch_id.strip() if batch_id else None

        if not any((number, guid, batch_id, product_item_guid)):
            raise EmptyVeterinaryDocumentError()

        return cls(
            id=uuid7(),
            org_unit_id=org_unit_id,
            number=number or None,
            guid=guid,
            batch_id=batch_id or None,
            product_item_guid=product_item_guid,
            source=VeterinaryDocumentSource.MANUAL,
            created_by=created_by,
            created_at=get_datetime_utc(),
        )
