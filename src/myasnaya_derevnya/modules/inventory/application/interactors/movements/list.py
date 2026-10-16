from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import MovementListItem
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.movement.base import (
    MovementReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListMovementsQuery:
    org_unit_id: UUID | None = None
    nomenclature_id: UUID | None = None
    movement_types: tuple[str, ...] = ()
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class MovementPage:
    items: list[MovementListItem]
    total: int
    limit: int
    offset: int


class ListMovementsInteractor:
    """Регистр движений: приход и расход по локации, номенклатуре и партии."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        movement_reader: MovementReader,
        catalog_api: CatalogAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._movement_reader = movement_reader
        self._catalog_api = catalog_api
        self._staff_api = staff_api

    async def __call__(self, query: ListMovementsQuery) -> MovementPage:
        current_user_id = await self._identity_provider.get_current_user_id()

        scope = await self._staff_api.scope_for(
            user_id=current_user_id, permission=READ_BALANCES
        )
        if scope.is_empty():
            raise ForbiddenError()

        if query.org_unit_id is not None:
            location = await self._business_api.stock_location(query.org_unit_id)
            if location is None:
                raise LocationNotFoundError(query.org_unit_id)

        narrowed = scope.narrow(query.org_unit_id)
        if narrowed is not None and not narrowed:
            raise ForbiddenError()

        org_unit_ids = None if narrowed is None else sorted(narrowed)

        cost_scope = await self._staff_api.scope_for(
            user_id=current_user_id, permission=READ_COSTS
        )

        items, total = await self._movement_reader.list(
            org_unit_ids=org_unit_ids,
            nomenclature_id=query.nomenclature_id,
            movement_types=query.movement_types,
            occurred_from=query.occurred_from,
            occurred_to=query.occurred_to,
            limit=query.limit,
            offset=query.offset,
        )

        names = await self._catalog_api.nomenclature_names(
            {item.nomenclature_id for item in items}
        )
        location_names = {
            location.id: location.name
            for location in await self._business_api.stock_locations()
        }

        return MovementPage(
            items=[
                replace(
                    item,
                    nomenclature_name=names.get(item.nomenclature_id),
                    location_name=location_names.get(item.org_unit_id),
                    total_cost_kopecks=(
                        item.total_cost_kopecks
                        if cost_scope.covers(item.org_unit_id)
                        else None
                    ),
                )
                for item in items
            ],
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
