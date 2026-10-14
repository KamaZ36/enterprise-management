from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import WarehouseType
from myasnaya_derevnya.modules.inventory.domain.errors import (
    WarehouseInUseError,
    WarehouseNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import MANAGE_WAREHOUSES
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class UpdateWarehouseCommand:
    warehouse_id: UUID
    name: str | None = None
    type_: WarehouseType | None = None
    is_active: bool | None = None


class UpdateWarehouseInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        balance_repository: StockBalanceRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._balance_repository = balance_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateWarehouseCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        warehouse = await self._warehouse_repository.get_by_id(command.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(command.warehouse_id)


        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=MANAGE_WAREHOUSES,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        if command.type_ is not None and command.type_ is not warehouse.type:
            if await self._balance_repository.has_any_for_warehouse(warehouse.id):
                raise WarehouseInUseError(warehouse.id)
            warehouse.change_type(command.type_)

        if command.name is not None:
            warehouse.rename(command.name)

        if command.is_active is not None:
            warehouse.activate() if command.is_active else warehouse.deactivate()

        await self._warehouse_repository.save(warehouse)
        await self._transaction_manager.commit()
