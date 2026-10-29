import hashlib

import pytest

from myasnaya_derevnya.modules.pos.domain.errors import (
    InvalidDokaGuidError,
    InvalidDokaOrgIdError,
)
from myasnaya_derevnya.modules.pos.domain.value_objects.api_key import (
    api_key_prefix,
    generate_api_key,
    hash_api_key,
)
from myasnaya_derevnya.modules.pos.domain.value_objects.identifiers import (
    canonicalize_guid,
    normalize_doka_org_id,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("27DE775614AD4D17A482B578611C605C915612757914", "27DE775614AD4D17A482B578611C605C915612757914"),
        ("27de7756-14ad-4d17-a482-b578611c605c915612757914", "27DE775614AD4D17A482B578611C605C915612757914"),
        ("a0f13aa4-7af4-468f-8cd2-ef7cf14e3674", "A0F13AA47AF4468F8CD2EF7CF14E3674"),
    ],
)
def test_canonicalize_guid_accepts_doka_forms(raw: str, expected: str) -> None:
    assert canonicalize_guid(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "27DE7756",
        "27DE775614AD4D17A482B578611C605C91561275791",
        "GGGG775614AD4D17A482B578611C605C915612757914",
    ],
)
def test_canonicalize_guid_rejects_broken_values(raw: str) -> None:
    with pytest.raises(InvalidDokaGuidError):
        canonicalize_guid(raw)


def test_normalize_doka_org_id_requires_digits() -> None:
    assert normalize_doka_org_id(" 915612757914 ") == "915612757914"

    with pytest.raises(InvalidDokaOrgIdError):
        normalize_doka_org_id("915-612")
    with pytest.raises(InvalidDokaOrgIdError):
        normalize_doka_org_id("")


def test_api_key_is_hashed_by_sha256_and_never_repeats() -> None:
    first = generate_api_key()
    second = generate_api_key()

    assert first != second
    assert hash_api_key(first) == hashlib.sha256(first.encode()).hexdigest()
    assert api_key_prefix(first) == first[:8]
    assert len(first) > 32
