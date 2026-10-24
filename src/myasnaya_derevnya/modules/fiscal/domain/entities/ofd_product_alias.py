from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.fiscal.domain.value_objects.barcode import (
    normalize_barcode,
)
from myasnaya_derevnya.utils import get_datetime_utc


class OfdProductAlias:
    """Сохранённое соответствие штрихкода ОФД и номенклатуры."""

    def __init__(
        self,
        id: UUID,
        barcode: str,
        nomenclature_id: UUID,
        created_by: UUID | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._barcode = barcode
        self._nomenclature_id = nomenclature_id
        self._created_by = created_by
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        barcode: str,
        nomenclature_id: UUID,
        created_by: UUID | None,
    ) -> OfdProductAlias:
        normalized = normalize_barcode(barcode)
        if normalized is None:
            raise ValueError("Пустой штрихкод нельзя сохранить как соответствие.")

        now = get_datetime_utc()
        return cls(
            id=uuid7(),
            barcode=normalized,
            nomenclature_id=nomenclature_id,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def barcode(self) -> str:
        return self._barcode

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def change_nomenclature(self, nomenclature_id: UUID) -> None:
        self._nomenclature_id = nomenclature_id
        self._updated_at = get_datetime_utc()
