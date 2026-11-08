from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.catalog.domain.errors import (
    EmptyNameError,
    EmptySkuError,
    InvalidGtinError,
)
from myasnaya_derevnya.utils import get_datetime_utc


class UnitOfMeasurement(StrEnum):
    KG = "kg"
    GRAM = "g"
    PIECE = "pcs"
    LITER = "l"
    METER = "m"


GTIN_LENGTHS = frozenset({8, 13, 14})


def normalize_gtin(gtin: str | None) -> str | None:
    """Возвращает GTIN без пробелов или ``None``, если значение пустое."""

    normalized = gtin.strip() if gtin else ""

    return normalized or None


def validate_gtin(gtin: str | None) -> str | None:
    normalized = normalize_gtin(gtin)
    if normalized is None:
        return None

    if not normalized.isdigit() or len(normalized) not in GTIN_LENGTHS:
        raise InvalidGtinError(normalized)

    return normalized


class Nomenclature:
    def __init__(
        self,
        id: UUID,
        sku: str,
        name: str,
        unit: UnitOfMeasurement,
        category_id: UUID,
        created_at: datetime,
        is_active: bool = True,
        image_url: str | None = None,
        description: str | None = None,
        requires_vetis: bool = False,
        gtin: str | None = None,
    ) -> None:
        self._id = id
        self._sku = sku
        self._name = name
        self._unit = unit
        self._category_id = category_id
        self._created_at = created_at
        self._is_active = is_active
        self._image_url = image_url
        self._description = description
        self._requires_vetis = requires_vetis
        self._gtin = normalize_gtin(gtin)

    @classmethod
    def create(
        cls,
        sku: str,
        name: str,
        unit: UnitOfMeasurement,
        category_id: UUID,
        image_url: str | None = None,
        description: str | None = None,
        requires_vetis: bool = False,
        gtin: str | None = None,
    ) -> Nomenclature:
        if not name.strip():
            raise EmptyNameError()
        if not sku:
            raise EmptySkuError()

        return cls(
            id=uuid7(),
            sku=sku,
            name=name,
            unit=unit,
            category_id=category_id,
            created_at=get_datetime_utc(),
            image_url=image_url,
            description=description,
            requires_vetis=requires_vetis,
            gtin=validate_gtin(gtin),
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
    def unit(self) -> UnitOfMeasurement:
        return self._unit

    @property
    def category_id(self) -> UUID:
        return self._category_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def image_url(self) -> str | None:
        return self._image_url

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def requires_vetis(self) -> bool:
        return self._requires_vetis

    @property
    def gtin(self) -> str | None:
        return self._gtin

    def change_gtin(self, gtin: str | None) -> None:
        self._gtin = validate_gtin(gtin)

    def change_vetis_requirement(self, requires_vetis: bool) -> None:
        self._requires_vetis = requires_vetis

    def rename(self, name: str) -> None:
        if not name.strip():
            raise EmptyNameError()
        self._name = name.strip()

    def change_image_url(self, image_url: str | None) -> None:
        cleaned = image_url.strip() if image_url else None
        self._image_url = cleaned or None

    def change_description(self, description: str | None) -> None:
        cleaned = description.strip() if description else None
        self._description = cleaned or None

    def change_category(self, category_id: UUID) -> None:
        self._category_id = category_id

    def change_unit(self, unit: UnitOfMeasurement) -> None:
        self._unit = unit

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True
