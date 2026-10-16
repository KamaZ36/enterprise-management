from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.production.application.dto import ProductionOrderPage
from myasnaya_derevnya.modules.production.domain.permissions import READ_ORDERS
from myasnaya_derevnya.modules.production.infrastructure.readers.production_order.base import (
    ProductionOrderReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListProductionOrdersQuery:
    org_unit_id: UUID | None = None
    statuses: tuple[str, ...] | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    limit: int = 50
    offset: int = 0


class ListProductionOrdersInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        inventory_api: InventoryAPI,
        order_reader: ProductionOrderReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._inventory_api = inventory_api
        self._order_reader = order_reader

    async def __call__(
        self, query: ListProductionOrdersQuery
    ) -> ProductionOrderPage:
        user_id = await self._identity_provider.get_current_user_id()

        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=READ_ORDERS
        )
        if scope.is_empty():
            raise ForbiddenError()

        org_unit_ids = await self._visible_org_unit_ids(scope)

        if query.org_unit_id is not None:
            if org_unit_ids is not None and query.org_unit_id not in org_unit_ids:
                raise ForbiddenError()

            org_unit_ids = [query.org_unit_id]

        items, total = await self._order_reader.list(
            org_unit_ids=org_unit_ids,
            statuses=query.statuses,
            occurred_from=query.occurred_from,
            occurred_to=query.occurred_to,
            limit=query.limit,
            offset=query.offset,
        )

        names: dict[UUID, str] = {}
        if items:
            for org_unit_id in {item.org_unit_id for item in items}:
                location = await self._inventory_api.get_location(org_unit_id)
                if location is not None:
                    names[org_unit_id] = location.name

            items = [
                replace(item, location_name=names.get(item.org_unit_id))
                for item in items
            ]

        return ProductionOrderPage(items=items, total=total)

    async def _visible_org_unit_ids(self, scope) -> list[UUID] | None:
        if scope.is_company_wide:
            return None

        locations = await self._inventory_api.list_locations()
        visible = sorted(
            location.id
            for location in locations
            if scope.covers(location.id)
        )

        if not visible:
            raise ForbiddenError()

        return visible
