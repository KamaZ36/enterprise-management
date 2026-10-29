from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.pos.domain.errors import InvalidUnitFactorError
from myasnaya_derevnya.modules.pos.domain.value_objects.identifiers import (
    canonicalize_guid,
)
from myasnaya_derevnya.utils import get_datetime_utc


class PosProductMapping:
    """Сопоставление товара DoKa с номенклатурой."""

    def __init__(
        self,
        id: UUID,
        source_id: UUID,
        doka_product_guid: str,
        nomenclature_id: UUID,
        unit_factor: Decimal,
        is_active: bool,
        created_by: UUID | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._source_id = source_id
        self._doka_product_guid = doka_product_guid
        self._nomenclature_id = nomenclature_id
        self._unit_factor = unit_factor
        self._is_active = is_active
        self._created_by = created_by
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        source_id: UUID,
        doka_product_guid: str,
        nomenclature_id: UUID,
        unit_factor: Decimal,
        created_by: UUID | None = None,
    ) -> PosProductMapping:
        now = get_datetime_utc()

        return cls(
            id=uuid7(),
            source_id=source_id,
            doka_product_guid=canonicalize_guid(doka_product_guid),
            nomenclature_id=nomenclature_id,
            unit_factor=_positive_factor(unit_factor),
            is_active=True,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def source_id(self) -> UUID:
        return self._source_id

    @property
    def doka_product_guid(self) -> str:
        return self._doka_product_guid

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def unit_factor(self) -> Decimal:
        return self._unit_factor

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(
        self,
        *,
        nomenclature_id: UUID | None = None,
        unit_factor: Decimal | None = None,
        is_active: bool | None = None,
    ) -> None:
        if nomenclature_id is not None:
            self._nomenclature_id = nomenclature_id
        if unit_factor is not None:
            self._unit_factor = _positive_factor(unit_factor)
        if is_active is not None:
            self._is_active = is_active

        self._updated_at = get_datetime_utc()


def _positive_factor(value: Decimal) -> Decimal:
    if value <= 0:
        raise InvalidUnitFactorError()

    return value
