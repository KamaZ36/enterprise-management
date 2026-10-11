from abc import ABC, abstractmethod
from decimal import Decimal

from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money


class CostPolicy(ABC):
    @abstractmethod
    def issue_cost(
        self,
        *,
        quantity_out: Decimal,
        balance_quantity: Decimal,
        balance_total: Money,
    ) -> Money:
        raise NotImplementedError


class MovingAverageCostPolicy(CostPolicy):
    def issue_cost(
        self,
        *,
        quantity_out: Decimal,
        balance_quantity: Decimal,
        balance_total: Money,
    ) -> Money:
        if quantity_out == balance_quantity:
            return balance_total

        average_unit_cost = balance_total.rubles / balance_quantity
        return Money.from_quantity_and_unit_cost(quantity_out, average_unit_cost)
