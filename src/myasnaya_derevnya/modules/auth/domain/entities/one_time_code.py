from datetime import datetime, timedelta
from uuid import UUID, uuid4

from myasnaya_derevnya.utils import get_datetime_utc


class OneTimeCode:
    def __init__(
        self,
        id: UUID,
        identifier: str,
        code_hash: str,
        expires_at: datetime,
        attempts: int,
        max_attempts: int,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._identifier = identifier
        self._code_hash = code_hash
        self._expires_at = expires_at
        self._attempts = attempts
        self._max_attempts = max_attempts
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        identifier: str,
        code_hash: str,
        ttl: timedelta,
        max_attempts: int,
    ) -> OneTimeCode:
        now = get_datetime_utc()

        return cls(
            id=uuid4(),
            identifier=identifier,
            code_hash=code_hash,
            expires_at=now + ttl,
            attempts=0,
            max_attempts=max_attempts,
            created_at=now,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self._expires_at

    @property
    def attempts_exhausted(self) -> bool:
        return self._attempts >= self._max_attempts

    def matches(self, code_hash: str) -> bool:
        return self._code_hash == code_hash

    def register_failed_attempt(self) -> None:
        self._attempts += 1

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def code_hash(self) -> str:
        return self._code_hash

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def created_at(self) -> datetime:
        return self._created_at
