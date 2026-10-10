from abc import ABC, abstractmethod
from decimal import Decimal

from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money


class CostPolicy(ABC):
    """Политика оценки расхода: сейчас средневзвешенная, дальше возможен FIFO."""

    @abstractmethod
    def issue_cost(
        self,
        *,
        quantity_out: Decimal,
        balance_quantity: Decimal,
        balance_total: Money,
    ) -> Money:
        """Себестоимость списываемого количества.

        Предусловие: 0 < quantity_out <= balance_quantity.
        """
        raise NotImplementedError


class MovingAverageCostPolicy(CostPolicy):
    """Средневзвешенная скользящая себестоимость."""

    def issue_cost(
        self,
        *,
        quantity_out: Decimal,
        balance_quantity: Decimal,
        balance_total: Money,
    ) -> Money:
        if quantity_out == balance_quantity:
            # Полное списание забирает остаток целиком: иначе от округления
            # на складе навсегда останутся «висячие» копейки.
            return balance_total

        average_unit_cost = balance_total.rubles / balance_quantity
        return Money.from_quantity_and_unit_cost(quantity_out, average_unit_cost)
