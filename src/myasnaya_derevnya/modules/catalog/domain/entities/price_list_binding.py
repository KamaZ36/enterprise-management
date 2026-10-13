from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class PriceListBinding:
    def __init__(
        self, id_: UUID, org_unit_id: UUID, price_list_id: UUID, created_at: datetime
    ) -> None:
        self._id = id_
        self._org_unit_id = org_unit_id
        self._price_list_id = price_list_id
        self._created_at = created_at

    @classmethod
    def create(cls, org_unit_id: UUID, price_list_id: UUID) -> PriceListBinding:
        return cls(
            id_=uuid7(),
            org_unit_id=org_unit_id,
            price_list_id=price_list_id,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def price_list_id(self) -> UUID:
        return self._price_list_id

    @property
    def created_at(self) -> datetime:
        return self._created_at
