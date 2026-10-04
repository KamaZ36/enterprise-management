from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class UserIdentityType(StrEnum):
    USERNAME = "username"
    PHONE_NUMBER = "phone_number"


class UserIdentity:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        identity_type: UserIdentityType,
        identifier: str,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._identity_type = identity_type
        self._identifier = identifier
        self._created_at = created_at

    @classmethod
    def create(
        cls, user_id: UUID, identity_type: UserIdentityType, identifier: str
    ) -> UserIdentity:
        return cls(
            id=uuid7(),
            user_id=user_id,
            identity_type=identity_type,
            identifier=identifier,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def identity_type(self) -> UserIdentityType:
        return self._identity_type

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def created_at(self) -> datetime:
        return self._created_at
