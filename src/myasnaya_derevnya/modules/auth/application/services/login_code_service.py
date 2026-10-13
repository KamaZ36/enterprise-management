import hashlib
import hmac
import secrets
from datetime import timedelta


class LoginCodeService:
    def __init__(
        self,
        *,
        secret: str,
        code_length: int,
        ttl: timedelta,
        max_attempts: int,
        min_interval: timedelta,
        hourly_limit: int,
    ) -> None:
        self._secret = secret.encode()
        self._code_length = code_length
        self._ttl = ttl
        self._max_attempts = max_attempts
        self._min_interval = min_interval
        self._hourly_limit = hourly_limit

    def generate(self) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(self._code_length))

    def hash(self, identifier: str, code: str) -> str:
        payload = f"{identifier}:{code}".encode()
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    @property
    def ttl(self) -> timedelta:
        return self._ttl

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def min_interval(self) -> timedelta:
        return self._min_interval

    @property
    def hourly_limit(self) -> int:
        return self._hourly_limit
