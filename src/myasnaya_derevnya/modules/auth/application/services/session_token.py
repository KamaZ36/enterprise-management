import hashlib
import secrets
from uuid import UUID

TOKEN_BYTES = 32
TOKEN_MAX_LENGTH = 512


def generate_session_token() -> str:
    """Непрозрачный токен сессии. Клиент шлёт его в `Authorization: Bearer`."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """В БД хранится только хэш: утечка базы не даёт готовых токенов.

    Токен имеет 256 бит энтропии, поэтому достаточно детерминированного
    SHA-256 — он нужен для поиска сессии по токену.

    Старые сессии использовали UUID в качестве токена. Канонизируем такие
    значения, чтобы токен в верхнем регистре тоже находил свою сессию.
    """
    try:
        token = str(UUID(token))
    except ValueError:
        pass

    return hashlib.sha256(token.encode()).hexdigest()
