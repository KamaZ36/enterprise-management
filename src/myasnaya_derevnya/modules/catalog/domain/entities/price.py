from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.catalog.domain.errors import NegativePriceValueError
from myasnaya_derevnya.utils import get_datetime_utc


class Price:
    def __init__(
        self,
        id_: UUID,
        nomenclature_id: UUID,
        price_list_id: UUID,
        value: int,
        updated_at: datetime,
    ) -> None:
        self._id = id_
        self._nomenclature_id = nomenclature_id
        self._price_list_id = price_list_id
        self._value = value
        self._updated_at = updated_at

    @classmethod
    def create(cls, nomenclature_id: UUID, price_list_id: UUID, value: int) -> Price:
        if value < 0:
            raise NegativePriceValueError()

        return cls(
            id_=uuid7(),
            nomenclature_id=nomenclature_id,
            price_list_id=price_list_id,
            value=value,
            updated_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def price_list_id(self) -> UUID:
        return self._price_list_id

    @property
    def value(self) -> int:
        return self._value

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_value(self, new_value: int) -> None:
        if new_value < 0:
            raise NegativePriceValueError()

        self._value = new_value
        self._updated_at = get_datetime_utc()
