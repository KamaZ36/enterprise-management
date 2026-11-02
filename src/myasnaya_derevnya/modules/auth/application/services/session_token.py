import hashlib
import secrets
from uuid import UUID

TOKEN_BYTES = 32
TOKEN_MAX_LENGTH = 512


def generate_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    try:
        token = str(UUID(token))
    except ValueError:
        pass

    return hashlib.sha256(token.encode()).hexdigest()
