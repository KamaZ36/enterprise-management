from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

KOPEKS_PER_RUBLE = Decimal(100)


@dataclass(frozen=True, slots=True)
class Money:
    """Денежная сумма в копейках: сложение и вычитание точные."""

    kopecks: int

    @classmethod
    def zero(cls) -> Money:
        return cls(kopecks=0)

    @classmethod
    def from_rubles(cls, value: Decimal) -> Money:
        rounded = (value * KOPEKS_PER_RUBLE).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
        return cls(kopecks=int(rounded))

    @classmethod
    def from_quantity_and_unit_cost(
        cls, quantity: Decimal, unit_cost: Decimal
    ) -> Money:
        return cls.from_rubles(quantity * unit_cost)

    @property
    def rubles(self) -> Decimal:
        return Decimal(self.kopecks) / KOPEKS_PER_RUBLE

    @property
    def is_zero(self) -> bool:
        return self.kopecks == 0

    @property
    def is_negative(self) -> bool:
        return self.kopecks < 0

    def __add__(self, other: Money) -> Money:
        return Money(kopecks=self.kopecks + other.kopecks)

    def __sub__(self, other: Money) -> Money:
        return Money(kopecks=self.kopecks - other.kopecks)

    def __neg__(self) -> Money:
        return Money(kopecks=-self.kopecks)

    def __str__(self) -> str:
        return f"{self.rubles:.2f}"
