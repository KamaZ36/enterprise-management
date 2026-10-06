from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.catalog.domain.errors import (
    EmptyNameError,
    EmptySkuError,
)
from myasnaya_derevnya.utils import get_datetime_utc


class NomenclatureType(StrEnum):
    RAW_MATERIAL = "raw_material"  # Сырье (мясо, специи, соль)
    SEMI_FINISHED = "semi_finished"  # Полуфабрикат (фарш, тесто)
    FINISHED_GOOD = "finished_good"  # Готовая продукция (колбаса, бургер)


class UnitOfMeasurement(StrEnum):
    KG = "kg"
    GRAM = "g"
    PIECE = "pcs"
    LITER = "l"
    METER = "m"


class Nomenclature:
    def __init__(
        self,
        id: UUID,
        sku: str,
        name: str,
        type_: NomenclatureType,
        category_id: UUID,
        gtin: str | None,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._sku = sku
        self._name = name
        self._type = type_
        self._category_id = category_id
        self._gtin = gtin
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        sku: str,
        name: str,
        type_: NomenclatureType,
        category_id: UUID,
        gtin: str | None,
    ) -> Nomenclature:
        if not name.strip():
            raise EmptyNameError()
        if not sku:
            raise EmptySkuError()

        return cls(
            id=uuid7(),
            sku=sku,
            name=name,
            type_=type_,
            category_id=category_id,
            gtin=gtin,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def name(self) -> str:
        return self._name

    @property
    def gtin(self) -> str | None:
        return self._gtin
