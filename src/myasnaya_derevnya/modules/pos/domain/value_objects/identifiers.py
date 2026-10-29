import re

from myasnaya_derevnya.modules.pos.domain.errors import (
    InvalidDokaGuidError,
    InvalidDokaOrgIdError,
)

_GUID_LENGTHS = frozenset({32, 44})
_ORG_ID_PATTERN = re.compile(r"^\d{1,32}$")


def canonicalize_guid(value: str) -> str:
    """Приводит GUID DoKa к виду: верхний регистр, только hex-символы."""

    canonical = re.sub(r"[^0-9A-Fa-f]", "", value).upper()

    if len(canonical) not in _GUID_LENGTHS:
        raise InvalidDokaGuidError()

    return canonical


def normalize_doka_org_id(value: str) -> str:
    normalized = value.strip()

    if not _ORG_ID_PATTERN.fullmatch(normalized):
        raise InvalidDokaOrgIdError()

    return normalized
