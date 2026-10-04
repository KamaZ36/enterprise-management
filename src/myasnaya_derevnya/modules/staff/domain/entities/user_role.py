from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class UserRole:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        role_id: UUID,
        location_id: UUID | None,
        created_at: datetime,
        created_by: UUID,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._role_id = role_id
        self._location_id = location_id
        self._created_at = created_at
        self._created_by = created_by

    @classmethod
    def create(
        cls, user_id: UUID, role_id: UUID, location_id: UUID | None, created_by: UUID
    ) -> UserRole:
        return cls(
            id=uuid7(),
            user_id=user_id,
            role_id=role_id,
            location_id=location_id,
            created_at=get_datetime_utc(),
            created_by=created_by,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def role_id(self) -> UUID:
        return self._role_id

    @property
    def location_id(self) -> UUID | None:
        return self._location_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def created_by(self) -> UUID:
        return self._created_by
