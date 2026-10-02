import bcrypt

from myasnaya_derevnya.user_service.infrastructure.services.password.base import (
    PasswordService,
)


class BcryptPasswordService(PasswordService):
    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash_password(self, password: str) -> str:
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        return hashed_bytes.decode("utf-8")

    def verify(self, password: str, hashed_password: str) -> bool:
        try:
            password_bytes = password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except ValueError, TypeError:
            return False
