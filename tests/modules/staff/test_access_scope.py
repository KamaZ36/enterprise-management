from uuid import uuid7

from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


def test_company_wide_scope_covers_everything_and_does_not_filter() -> None:
    scope = AccessScope.company_wide()

    assert not scope.is_empty()
    point = uuid7()

    assert scope.covers(point)
    # без запрошенной точки фильтра нет, с точкой — сужаемся до неё
    assert scope.narrow(None) is None
    assert scope.narrow(point) == frozenset({point})


def test_empty_scope_is_empty_and_covers_nothing() -> None:
    scope = AccessScope.of([])

    assert scope.is_empty()
    assert not scope.covers(uuid7())
    assert scope.narrow(None) == frozenset()
    assert scope.narrow(uuid7()) == frozenset()


def test_scope_of_points_narrows_to_requested_one() -> None:
    point, other = uuid7(), uuid7()
    scope = AccessScope.of({point})

    assert not scope.is_empty()
    assert scope.covers(point)
    assert scope.narrow(point) == frozenset({point})
    assert scope.narrow(other) == frozenset()
    assert scope.narrow(None) == frozenset({point})
