from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.stock_balance import (
    StockBalance,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    EmptyMovementError,
    InsufficientStockError,
    NegativeCostError,
)
from myasnaya_derevnya.modules.inventory.domain.services.cost_policy import (
    MovingAverageCostPolicy,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money

POLICY = MovingAverageCostPolicy()


def make_balance() -> StockBalance:
    return StockBalance.empty(warehouse_id=uuid4(), nomenclature_id=uuid4())


def test_empty_balance_has_zero_everything() -> None:
    balance = make_balance()

    assert balance.quantity == Decimal(0)
    assert balance.total_value.kopecks == 0
    assert balance.average_unit_cost == Decimal(0)


def test_receive_sets_quantity_and_value() -> None:
    balance = make_balance()

    balance.receive(Decimal(10), Money(kopecks=450000))

    assert balance.quantity == Decimal(10)
    assert balance.total_value.kopecks == 450000
    assert balance.average_unit_cost == Decimal(450)


def test_receive_twice_gives_weighted_average() -> None:
    balance = make_balance()

    balance.receive(Decimal(10), Money(kopecks=450000))  # 10 кг по 450
    balance.receive(Decimal(5), Money(kopecks=240000))  # 5 кг по 480

    assert balance.quantity == Decimal(15)
    assert balance.total_value.kopecks == 690000
    assert balance.average_unit_cost == Decimal(460)


def test_issue_uses_average_cost() -> None:
    balance = make_balance()
    balance.receive(Decimal(10), Money(kopecks=450000))
    balance.receive(Decimal(5), Money(kopecks=240000))

    cost = balance.issue(Decimal(3), POLICY)

    assert cost.kopecks == 138000  # 3 кг по 460
    assert balance.quantity == Decimal(12)
    assert balance.total_value.kopecks == 552000


def test_full_issue_takes_whole_remainder() -> None:
    """3 единицы за 100 копеек: средняя не делится нацело.

    Если бы каждое списание считалось как round(qty * avg), на складе
    навсегда остался бы «висячий» копеечный хвост.
    """
    balance = make_balance()
    balance.receive(Decimal(3), Money(kopecks=100))

    first = balance.issue(Decimal(1), POLICY)
    second = balance.issue(Decimal(1), POLICY)
    third = balance.issue(Decimal(1), POLICY)

    assert (first.kopecks, second.kopecks, third.kopecks) == (33, 34, 33)
    assert first.kopecks + second.kopecks + third.kopecks == 100
    assert balance.quantity == Decimal(0)
    assert balance.total_value.kopecks == 0
    assert balance.average_unit_cost == Decimal(0)


def test_sum_of_movements_equals_balance() -> None:
    balance = make_balance()
    balance.receive(Decimal(7), Money(kopecks=1051))
    balance.receive(Decimal(3), Money(kopecks=333))

    issued = balance.issue(Decimal(4), POLICY)

    assert balance.total_value.kopecks == 1051 + 333 - issued.kopecks


def test_issue_more_than_available_raises() -> None:
    balance = make_balance()
    balance.receive(Decimal(2), Money(kopecks=1000))
    nomenclature_id = balance.nomenclature_id

    with pytest.raises(InsufficientStockError) as error:
        balance.issue(Decimal("2.5"), POLICY)

    assert error.value.available == Decimal(2)
    assert error.value.requested == Decimal("2.5")
    assert error.value.nomenclature_id == nomenclature_id
    assert balance.quantity == Decimal(2)


def test_issue_from_empty_balance_raises_insufficient_stock() -> None:
    balance = make_balance()

    with pytest.raises(InsufficientStockError):
        balance.issue(Decimal(1), POLICY)


def test_issue_zero_or_negative_quantity_raises() -> None:
    balance = make_balance()
    balance.receive(Decimal(1), Money(kopecks=100))

    with pytest.raises(EmptyMovementError):
        balance.issue(Decimal(0), POLICY)

    with pytest.raises(EmptyMovementError):
        balance.issue(Decimal(-1), POLICY)


def test_receive_zero_quantity_raises() -> None:
    balance = make_balance()

    with pytest.raises(EmptyMovementError):
        balance.receive(Decimal(0), Money(kopecks=100))


def test_receive_negative_cost_raises() -> None:
    balance = make_balance()

    with pytest.raises(NegativeCostError):
        balance.receive(Decimal(1), Money(kopecks=-100))
