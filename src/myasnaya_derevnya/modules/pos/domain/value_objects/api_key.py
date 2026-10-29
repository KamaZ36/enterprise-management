import hashlib
import secrets

API_KEY_BYTES = 32
API_KEY_PREFIX_LENGTH = 8


def generate_api_key() -> str:
    return secrets.token_urlsafe(API_KEY_BYTES)


def hash_api_key(raw_key: str) -> str:
    """Хэш ключа агента.

    Ключ имеет высокую энтропию (32 случайных байта), поэтому достаточно
    SHA-256: медленный парольный хэш здесь не нужен и только замедлит
    каждый запрос агента.
    """

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def api_key_prefix(raw_key: str) -> str:
    return raw_key[:API_KEY_PREFIX_LENGTH]
