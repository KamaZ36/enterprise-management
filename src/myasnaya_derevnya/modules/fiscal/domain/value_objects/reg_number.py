from dataclasses import dataclass

from myasnaya_derevnya.modules.fiscal.domain.errors import InvalidRegNumberError

REG_NUMBER_LENGTH = 16


@dataclass(frozen=True, slots=True)
class RegNumber:
    """Регистрационный номер ККТ (РНМ) — ключ сопоставления с ОФД."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.isdigit() or len(self.value) != REG_NUMBER_LENGTH:
            raise InvalidRegNumberError()

    @classmethod
    def parse(cls, raw: str) -> RegNumber:
        """Разбирает пользовательский ввод: пробелы и дефисы допускаются."""
        return cls(value="".join(ch for ch in raw if ch not in " -"))

    def __str__(self) -> str:
        return self.value
