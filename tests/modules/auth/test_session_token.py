from uuid import uuid4

from myasnaya_derevnya.modules.auth.application.services.session_token import (
    generate_session_token,
    hash_session_token,
)


def test_tokens_are_unique_and_not_uuids() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert len(first) >= 32


def test_hash_is_deterministic_and_token_specific() -> None:
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)
    assert hash_session_token(token) != hash_session_token(generate_session_token())


def test_legacy_uuid_token_is_canonicalized() -> None:
    legacy = uuid4()

    assert hash_session_token(str(legacy).upper()) == hash_session_token(str(legacy))
