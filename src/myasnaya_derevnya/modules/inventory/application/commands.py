from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReceiptLineCommand:
    """Строка поступления: количество и цена — стоимость знает документ."""

    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal = Decimal(0)
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class WriteOffLineCommand:
    """Строка списания: цены нет, себестоимость определится при проведении."""

    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None = None
