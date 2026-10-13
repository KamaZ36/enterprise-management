import re

_NON_DIGITS = re.compile(r"\D")


def normalize_phone_number(raw: str) -> str | None:
    digits = _NON_DIGITS.sub("", raw)

    if len(digits) == 11 and digits[0] in {"7", "8"}:
        return f"+7{digits[1:]}"

    if len(digits) == 10:
        return f"+7{digits}"

    return None
