from decimal import Decimal

from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money


def test_zero() -> None:
    money = Money.zero()

    assert money.kopecks == 0
    assert money.is_zero is True
    assert money.is_negative is False


def test_from_rubles_rounds_half_up() -> None:
    assert Money.from_rubles(Decimal("10.005")).kopecks == 1001
    assert Money.from_rubles(Decimal("10.004")).kopecks == 1000


def test_from_rubles_negative_rounds_away_from_zero() -> None:
    assert Money.from_rubles(Decimal("-1.005")).kopecks == -101


def test_from_quantity_and_unit_cost() -> None:
    # 2.5 кг по 199.90 = 499.75
    money = Money.from_quantity_and_unit_cost(Decimal("2.5"), Decimal("199.90"))

    assert money.kopecks == 49975


def test_rubles_roundtrip() -> None:
    assert Money(kopecks=1500).rubles == Decimal(15)


def test_arithmetic() -> None:
    assert (Money(1000) + Money(255)).kopecks == 1255
    assert (Money(1000) - Money(255)).kopecks == 745
    assert (-Money(1000)).kopecks == -1000


def test_str_shows_rubles() -> None:
    assert str(Money(kopecks=1234)) == "12.34"
