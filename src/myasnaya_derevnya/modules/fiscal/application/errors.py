from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import NotFoundError


@dataclass(slots=True, eq=False)
class CashRegisterNotFound(NotFoundError):
    cash_register_id: UUID

    def __str__(self) -> str:
        return f"Касса {self.cash_register_id} не найдена."
