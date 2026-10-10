from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.errors import (
    EmptyMovementError,
    InsufficientLotStockError,
)


class StockLotBalance:
    """Остаток по партии: только количество, без стоимости."""

    def __init__(
        self,
        warehouse_id: UUID,
        nomenclature_id: UUID,
        lot_id: UUID,
        quantity: Decimal,
    ) -> None:
        self._warehouse_id = warehouse_id
        self._nomenclature_id = nomenclature_id
        self._lot_id = lot_id
        self._quantity = quantity

    @classmethod
    def empty(
        cls, warehouse_id: UUID, nomenclature_id: UUID, lot_id: UUID
    ) -> StockLotBalance:
        return cls(
            warehouse_id=warehouse_id,
            nomenclature_id=nomenclature_id,
            lot_id=lot_id,
            quantity=Decimal(0),
        )

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def lot_id(self) -> UUID:
        return self._lot_id

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    def receive(self, quantity: Decimal) -> None:
        if quantity <= 0:
            raise EmptyMovementError()
        self._quantity += quantity

    def issue(self, quantity: Decimal) -> None:
        if quantity <= 0:
            raise EmptyMovementError()
        if quantity > self._quantity:
            raise InsufficientLotStockError(
                lot_id=self._lot_id,
                available=self._quantity,
                requested=quantity,
            )
        self._quantity -= quantity
