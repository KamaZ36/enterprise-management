from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.errors import (
    EmptyMovementError,
    InsufficientStockError,
    NegativeCostError,
)
from myasnaya_derevnya.modules.inventory.domain.services.cost_policy import CostPolicy
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.utils import get_datetime_utc


class StockBalance:
    def __init__(
        self,
        org_unit_id: UUID,
        nomenclature_id: UUID,
        quantity: Decimal,
        total_value: Money,
        updated_at: datetime,
    ) -> None:
        self._org_unit_id = org_unit_id
        self._nomenclature_id = nomenclature_id
        self._quantity = quantity
        self._total_value = total_value
        self._updated_at = updated_at

    @classmethod
    def empty(cls, org_unit_id: UUID, nomenclature_id: UUID) -> StockBalance:
        return cls(
            org_unit_id=org_unit_id,
            nomenclature_id=nomenclature_id,
            quantity=Decimal(0),
            total_value=Money.zero(),
            updated_at=get_datetime_utc(),
        )

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def total_value(self) -> Money:
        return self._total_value

    @property
    def average_unit_cost(self) -> Decimal:
        if self._quantity == 0:
            return Decimal(0)
        return self._total_value.rubles / self._quantity

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def receive(self, quantity: Decimal, cost: Money) -> None:
        if quantity <= 0:
            raise EmptyMovementError()
        if cost.is_negative:
            raise NegativeCostError()

        self._quantity += quantity
        self._total_value = self._total_value + cost
        self._updated_at = get_datetime_utc()

    def issue(self, quantity: Decimal, policy: CostPolicy) -> Money:
        if quantity <= 0:
            raise EmptyMovementError()
        if quantity > self._quantity:
            raise InsufficientStockError(
                org_unit_id=self._org_unit_id,
                nomenclature_id=self._nomenclature_id,
                available=self._quantity,
                requested=quantity,
            )

        cost = policy.issue_cost(
            quantity_out=quantity,
            balance_quantity=self._quantity,
            balance_total=self._total_value,
        )

        self._quantity -= quantity
        self._total_value = self._total_value - cost

        if self._quantity == 0:
            self._total_value = Money.zero()

        self._updated_at = get_datetime_utc()

        return cost

    def release(self, quantity: Decimal, cost: Money) -> None:
        """Списывает количество и стоимость, посчитанную на уровне партии."""
        if quantity <= 0:
            raise EmptyMovementError()
        if quantity > self._quantity:
            raise InsufficientStockError(
                org_unit_id=self._org_unit_id,
                nomenclature_id=self._nomenclature_id,
                available=self._quantity,
                requested=quantity,
            )

        self._quantity -= quantity
        self._total_value = self._total_value - cost

        if self._quantity == 0:
            self._total_value = Money.zero()

        self._updated_at = get_datetime_utc()
