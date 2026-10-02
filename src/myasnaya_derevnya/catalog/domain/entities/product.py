from enum import StrEnum
from uuid import UUID, uuid7


class Unit(StrEnum):
    KG = "kg"
    MG = "mg"
    G = "g"

    L = "l"
    ML = "ml"


class ProductType(StrEnum):
    """Product type"""

    RAW_MATERIAL = "RAW_MATERIAL"
    MATERIAL = "MATERIAL"
    FINISHED_PRODUCT = "FINISHED_PRODUCT"
    DISH = "DISH"
    DRINK = "DRINK"


class Product:
    def __init__(
        self,
        id: UUID,
        name: str,
        product_type: ProductType,
        sku: int,
        unit: Unit,
        description: str,
        active: bool,
    ) -> None:
        self._id = id
        self._name = name
        self._product_type = product_type
        self._sku = sku
        self._unit = unit
        self._description = description
        self._active = active

    @classmethod
    def create(
        cls,
        name: str,
        product_type: ProductType,
        unit: Unit,
        description: str,
        sku: int,
    ) -> Product:
        return cls(
            id=uuid7(),
            name=name,
            product_type=product_type,
            sku=sku,
            unit=unit,
            description=description,
            active=True,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def product_type(self) -> ProductType:
        return self._product_type

    @property
    def sku(self) -> int:
        return self._sku

    @property
    def unit(self) -> Unit:
        return self._unit

    @property
    def description(self) -> str:
        return self._description

    @property
    def active(self) -> bool:
        return self._active

    def rename(self, new_name: str) -> None:
        self._name = new_name
