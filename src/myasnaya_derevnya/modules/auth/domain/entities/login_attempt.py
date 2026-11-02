from datetime import datetime, timedelta
from math import ceil


class LoginAttempt:
    """Счётчик неудачных попыток входа по логину.

    Живёт отдельно от пользователя: попытки по несуществующему логину тоже
    нужно ограничивать, иначе перебор имён становится бесплатным.
    """

    def __init__(
        self,
        identifier: str,
        failed_attempts: int,
        window_started_at: datetime,
        locked_until: datetime | None,
        updated_at: datetime,
    ) -> None:
        self._identifier = identifier
        self._failed_attempts = failed_attempts
        self._window_started_at = window_started_at
        self._locked_until = locked_until
        self._updated_at = updated_at

    @classmethod
    def create(cls, identifier: str, now: datetime) -> LoginAttempt:
        return cls(
            identifier=identifier,
            failed_attempts=0,
            window_started_at=now,
            locked_until=None,
            updated_at=now,
        )

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def failed_attempts(self) -> int:
        return self._failed_attempts

    @property
    def window_started_at(self) -> datetime:
        return self._window_started_at

    @property
    def locked_until(self) -> datetime | None:
        return self._locked_until

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def is_locked(self, now: datetime) -> bool:
        return self._locked_until is not None and now < self._locked_until

    def retry_after_seconds(self, now: datetime) -> int:
        if self._locked_until is None or now >= self._locked_until:
            return 0

        return max(1, ceil((self._locked_until - now).total_seconds()))

    def register_failure(
        self,
        now: datetime,
        *,
        max_attempts: int,
        window: timedelta,
        lockout: timedelta,
    ) -> None:
        if now - self._window_started_at >= window:
            self._failed_attempts = 0
            self._window_started_at = now
            self._locked_until = None

        self._failed_attempts += 1

        if self._failed_attempts >= max_attempts:
            self._locked_until = now + lockout

        self._updated_at = now
