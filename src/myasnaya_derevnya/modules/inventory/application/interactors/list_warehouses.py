from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import Warehouse
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_WAREHOUSES
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ListWarehousesInteractor:
    """Склады, доступные пользователю: фильтр по правам на орг-единицу."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._staff_api = staff_api

    async def __call__(self) -> list[Warehouse]:
        current_user_id = await self._identity_provider.get_current_user_id()

        warehouses = await self._warehouse_repository.list()

        allowed: list[Warehouse] = []
        for warehouse in warehouses:
            if await self._staff_api.can(
                user_id=current_user_id,
                permission=READ_WAREHOUSES,
                org_unit_id=warehouse.org_unit_id,
            ):
                allowed.append(warehouse)

        return allowed
