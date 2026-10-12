from myasnaya_derevnya.core.identity_provider import IdentityProvider
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
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_reader = warehouse_reader
        self._staff_api = staff_api

    async def __call__(self) -> list[WarehouseListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        warehouses = await self._warehouse_reader.list_all()

        allowed: list[WarehouseListItem] = []
        for warehouse in warehouses:
            if await self._staff_api.can(
                user_id=current_user_id,
                permission=READ_WAREHOUSES,
                org_unit_id=warehouse.org_unit_id,
            ):
                allowed.append(warehouse)

        return allowed
