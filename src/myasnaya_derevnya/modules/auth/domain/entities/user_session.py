from datetime import datetime
from uuid import UUID, uuid4

from myasnaya_derevnya.utils import get_datetime_utc


class UserSession:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        expires_at: datetime,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._expires_at = expires_at
        self._created_at = created_at

    @classmethod
    def create(cls, user_id: UUID, expires_at: datetime) -> UserSession:
        return cls(
            id=uuid4(),
            user_id=user_id,
            expires_at=expires_at,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def created_at(self) -> datetime:
        return self._created_at
