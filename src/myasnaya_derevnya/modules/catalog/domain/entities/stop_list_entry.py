from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class StopListEntry:
    """Товар, временно недоступный к продаже в конкретной точке."""

    def __init__(
        self,
        id_: UUID,
        org_unit_id: UUID,
        nomenclature_id: UUID,
        created_by: UUID | None,
        created_at: datetime,
    ) -> None:
        self._id = id_
        self._org_unit_id = org_unit_id
        self._nomenclature_id = nomenclature_id
        self._created_by = created_by
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        org_unit_id: UUID,
        nomenclature_id: UUID,
        created_by: UUID | None,
    ) -> StopListEntry:
        return cls(
            id_=uuid7(),
            org_unit_id=org_unit_id,
            nomenclature_id=nomenclature_id,
            created_by=created_by,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    @property
    def created_at(self) -> datetime:
        return self._created_at
