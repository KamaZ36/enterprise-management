from enum import StrEnum
from uuid import UUID, uuid7


class BusinessUnitType(StrEnum):
    PRODUCTION = "production"
    STORE = "store"
    CAFE = "cafe"


class BusinessUnit:
    def __init__(
        self,
        id: UUID,
        name: str,
        business_type: BusinessUnitType,
    ) -> None:
        self._id = id
        self._name = name
        self._business_type = business_type

    @classmethod
    def create(cls, name: str, business_type: BusinessUnitType) -> BusinessUnit:
        return cls(id=uuid7(), name=name, business_type=business_type)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def business_type(self) -> BusinessUnitType:
        return self._business_type
