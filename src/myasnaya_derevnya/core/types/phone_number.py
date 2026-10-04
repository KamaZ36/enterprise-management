from dataclasses import dataclass

import phonenumbers


class InvalidPhoneNumber(ValueError): ...


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    value: str  # E.164

    @classmethod
    def parse(cls, raw: str, default_region: str | None = "RU") -> PhoneNumber:
        cleaned = "".join(raw.split()).strip()

        if (
            cleaned.startswith("8")
            or cleaned.startswith("7")
            and not cleaned.startswith("+")
        ):
            cleaned = "+7" + cleaned[1:]

        try:
            parsed = phonenumbers.parse(raw, default_region)
        except phonenumbers.NumberParseException as e:
            raise InvalidPhoneNumber(raw) from e
        if not phonenumbers.is_valid_number(parsed):
            raise InvalidPhoneNumber(raw)
        return cls(
            phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        )

    def __str__(self) -> str:
        return self.value
