from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class PasswordLoginPolicy:
    max_attempts: int
    window: timedelta
    lockout: timedelta

    @property
    def retention(self) -> timedelta:
        """Сколько хранить счётчик, чтобы старые записи не копились."""
        return self.window + self.lockout
