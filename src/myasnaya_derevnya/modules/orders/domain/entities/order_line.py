from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.orders.domain.errors import (
    EmptyOrderLineError,
    NegativePriceError,
)


class OrderLine:
    def __init__(
        self,
        id_: UUID,
        nomenclature_id: UUID,
        quantity: Decimal,
        unit_price: int,
        cost_kopecks: int | None = None,
    ) -> None:
        self._id = id_
        self._nomenclature_id = nomenclature_id
        self._quantity = quantity
        self._unit_price = unit_price
        self._cost_kopecks = cost_kopecks

    @classmethod
    def create(
        cls, nomenclature_id: UUID, quantity: Decimal, unit_price: int
    ) -> OrderLine:
        if quantity <= 0:
            raise EmptyOrderLineError()

        if unit_price < 0:
            raise NegativePriceError()

        return cls(
            id_=uuid7(),
            nomenclature_id=nomenclature_id,
            quantity=quantity,
            unit_price=unit_price,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def unit_price(self) -> int:
        return self._unit_price

    @property
    def cost_kopecks(self) -> int | None:
        return self._cost_kopecks

    @property
    def total(self) -> int:
        return int(self._quantity * self._unit_price)

    @property
    def margin(self) -> int | None:
        if self._cost_kopecks is None:
            return None

        return self.total - self._cost_kopecks

    def set_cost(self, cost_kopecks: int) -> None:
        self._cost_kopecks = cost_kopecks
