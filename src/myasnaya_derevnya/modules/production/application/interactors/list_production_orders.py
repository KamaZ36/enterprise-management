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
    warehouse_id: UUID | None = None
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

        warehouse_ids = await self._visible_warehouse_ids(scope)

        if query.warehouse_id is not None:
            if warehouse_ids is not None and query.warehouse_id not in warehouse_ids:
                raise ForbiddenError()

            warehouse_ids = [query.warehouse_id]

        items, total = await self._order_reader.list(
            warehouse_ids=warehouse_ids,
            statuses=query.statuses,
            occurred_from=query.occurred_from,
            occurred_to=query.occurred_to,
            limit=query.limit,
            offset=query.offset,
        )

        names: dict[UUID, str] = {}
        if items:
            for warehouse_id in {item.warehouse_id for item in items}:
                warehouse = await self._inventory_api.get_warehouse(warehouse_id)
                if warehouse is not None:
                    names[warehouse_id] = warehouse.name

            items = [
                replace(item, warehouse_name=names.get(item.warehouse_id))
                for item in items
            ]

        return ProductionOrderPage(items=items, total=total)

    async def _visible_warehouse_ids(self, scope) -> list[UUID] | None:
        if scope.is_company_wide:
            return None

        warehouses = await self._inventory_api.list_warehouses()
        visible = sorted(
            warehouse.id
            for warehouse in warehouses
            if scope.covers(warehouse.org_unit_id)
        )

        if not visible:
            raise ForbiddenError()

        return visible
