from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.presentation.business_api import StockLocation
from myasnaya_derevnya.modules.inventory.application.dto import MovementListItem
from myasnaya_derevnya.modules.inventory.application.interactors.movements.list import (
    ListMovementsInteractor,
    ListMovementsQuery,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.presentation.api.v1.schemas import (
    MovementItemSchema,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    def __init__(self, locations: list[StockLocation]) -> None:
        self._locations = locations

    async def stock_location(self, org_unit_id: UUID) -> StockLocation | None:
        return next(
            (item for item in self._locations if item.id == org_unit_id), None
        )

    async def stock_locations(self) -> list[StockLocation]:
        return list(self._locations)


class FakeMovementReader:
    def __init__(self, items: list[MovementListItem]) -> None:
        self._items = items
        self.calls: list[dict] = []

    async def list(
        self,
        *,
        org_unit_ids=None,
        nomenclature_id=None,
        movement_types=(),
        occurred_from=None,
        occurred_to=None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MovementListItem], int]:
        self.calls.append(
            {
                "org_unit_ids": org_unit_ids,
                "nomenclature_id": nomenclature_id,
                "movement_types": tuple(movement_types),
                "occurred_from": occurred_from,
                "occurred_to": occurred_to,
                "limit": limit,
                "offset": offset,
            }
        )

        return list(self._items), len(self._items)


class FakeCatalogAPI:
    def __init__(self, names: dict[UUID, str] | None = None) -> None:
        self.names = names or {}

    async def nomenclature_names(self, nomenclature_ids) -> dict[UUID, str]:
        return {key: self.names[key] for key in nomenclature_ids if key in self.names}


class FakeStaffAPI:
    def __init__(self, scopes: dict[str, AccessScope] | None = None) -> None:
        self._scopes = scopes or {}

    async def scope_for(self, user_id: UUID, permission) -> AccessScope:
        return self._scopes.get(permission.code, AccessScope())


def make_location(name: str = "Основной цех") -> StockLocation:
    return StockLocation(id=uuid4(), code="PROD", name=name, is_active=True)


def make_movement(
    org_unit_id: UUID,
    nomenclature_id: UUID,
    *,
    movement_type: str = "receipt",
    quantity: str = "10",
    total_cost: int = 450000,
) -> MovementListItem:
    return MovementListItem(
        id=uuid4(),
        occurred_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        org_unit_id=org_unit_id,
        nomenclature_id=nomenclature_id,
        movement_type=movement_type,
        quantity=Decimal(quantity),
        total_cost_kopecks=total_cost,
    )


def build(
    locations: list[StockLocation],
    items: list[MovementListItem],
    *,
    scopes: dict[str, AccessScope] | None = None,
    names: dict[UUID, str] | None = None,
):
    reader = FakeMovementReader(items)
    interactor = ListMovementsInteractor(
        identity_provider=FakeIdentityProvider(),
        business_api=FakeBusinessAPI(locations),
        movement_reader=reader,
        catalog_api=FakeCatalogAPI(names),
        staff_api=FakeStaffAPI(scopes),
    )

    return interactor, reader


async def test_requires_read_balances_permission() -> None:
    location = make_location()
    interactor, reader = build([location], [])

    with pytest.raises(ForbiddenError):
        await interactor(ListMovementsQuery())

    assert reader.calls == []


async def test_raises_when_location_is_unknown() -> None:
    interactor, _ = build(
        [make_location()], [], scopes={READ_BALANCES.code: AccessScope.company_wide()}
    )

    with pytest.raises(LocationNotFoundError):
        await interactor(ListMovementsQuery(org_unit_id=uuid4()))


async def test_returns_items_with_names_and_signed_quantity() -> None:
    location = make_location()
    nomenclature_id = uuid4()
    item = make_movement(location.id, nomenclature_id)
    interactor, _ = build(
        [location],
        [item],
        scopes={
            READ_BALANCES.code: AccessScope.company_wide(),
            READ_COSTS.code: AccessScope.company_wide(),
        },
        names={nomenclature_id: "Говядина лопатка"},
    )

    page = await interactor(ListMovementsQuery())
    schema = MovementItemSchema.from_dto(page.items[0])

    assert page.total == 1
    assert schema.nomenclature_name == "Говядина лопатка"
    assert schema.location_name == "Основной цех"
    assert schema.movement_type == "receipt"
    assert schema.quantity == Decimal(10)
    assert schema.total_cost_kopecks == 450000


async def test_hides_cost_without_cost_permission() -> None:
    location = make_location()
    item = make_movement(location.id, uuid4())
    interactor, _ = build(
        [location], [item], scopes={READ_BALANCES.code: AccessScope.company_wide()}
    )

    page = await interactor(ListMovementsQuery())

    assert page.items[0].total_cost_kopecks is None


async def test_company_wide_scope_does_not_filter_locations() -> None:
    location = make_location()
    interactor, reader = build(
        [location], [], scopes={READ_BALANCES.code: AccessScope.company_wide()}
    )

    await interactor(ListMovementsQuery())

    assert reader.calls[0]["org_unit_ids"] is None


async def test_limited_scope_narrows_to_allowed_locations() -> None:
    allowed = make_location()
    denied = make_location()
    interactor, reader = build(
        [allowed, denied],
        [],
        scopes={READ_BALANCES.code: AccessScope.of([allowed.id])},
    )

    await interactor(ListMovementsQuery())

    assert reader.calls[0]["org_unit_ids"] == [allowed.id]


async def test_requested_location_outside_scope_is_forbidden() -> None:
    allowed = make_location()
    denied = make_location()
    interactor, _ = build(
        [allowed, denied],
        [],
        scopes={READ_BALANCES.code: AccessScope.of([allowed.id])},
    )

    with pytest.raises(ForbiddenError):
        await interactor(ListMovementsQuery(org_unit_id=denied.id))


async def test_passes_filters_and_pagination_through() -> None:
    location = make_location()
    nomenclature_id = uuid4()
    occurred_from = datetime(2026, 10, 1, tzinfo=UTC)
    interactor, reader = build(
        [location], [], scopes={READ_BALANCES.code: AccessScope.company_wide()}
    )

    await interactor(
        ListMovementsQuery(
            org_unit_id=location.id,
            nomenclature_id=nomenclature_id,
            movement_types=("sale", "write_off"),
            occurred_from=occurred_from,
            limit=20,
            offset=40,
        )
    )

    call = reader.calls[0]
    assert call["org_unit_ids"] == [location.id]
    assert call["nomenclature_id"] == nomenclature_id
    assert call["movement_types"] == ("sale", "write_off")
    assert call["occurred_from"] == occurred_from
    assert call["limit"] == 20
    assert call["offset"] == 40
