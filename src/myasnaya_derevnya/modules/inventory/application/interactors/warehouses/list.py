from dataclasses import replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.dto import WarehouseListItem
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_WAREHOUSES
from myasnaya_derevnya.modules.inventory.infrastructure.readers.warehouse.base import (
    WarehouseReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ListWarehousesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_reader: WarehouseReader,
        staff_api: StaffAPI,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_reader = warehouse_reader
        self._staff_api = staff_api
        self._business_api = business_api

    async def __call__(self, org_unit_id: UUID | None = None) -> list[WarehouseListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()


        scope = await self._staff_api.scope_for(
            user_id=current_user_id, permission=READ_WAREHOUSES
        )

        if scope.is_empty():
            return []

        allowed = scope.narrow(org_unit_id)
        if allowed is not None and not allowed:
            raise ForbiddenError()

        warehouses = await self._warehouse_reader.list_all()

        visible = [
            warehouse
            for warehouse in warehouses
            if allowed is None or warehouse.org_unit_id in allowed
        ]

        titles = await self._business_api.org_unit_titles(
            {warehouse.org_unit_id for warehouse in visible}
        )

        return [
            replace(warehouse, org_unit_name=titles.get(warehouse.org_unit_id))
            for warehouse in visible
        ]
