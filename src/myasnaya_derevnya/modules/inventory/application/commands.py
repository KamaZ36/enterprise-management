from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReceiptLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal = Decimal(0)
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class WriteOffLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None = None
