from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


class PasswordService:
    def __init__(self) -> None:
        self._hasher = _Argon2(
            time_cost=2,
            memory_cost=19456,
            parallelism=1,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            self._hasher.verify(password_hash, password)
        except VerifyMismatchError, VerificationError, InvalidHashError:
            return False
        return True
