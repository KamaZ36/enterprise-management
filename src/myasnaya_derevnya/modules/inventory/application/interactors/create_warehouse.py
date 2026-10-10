from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    OrgUnitNotFoundError,
    WarehouseCodeAlreadyExistsError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import MANAGE_WAREHOUSES
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateWarehouseCommand:
    org_unit_id: UUID
    code: str
    name: str
    type: WarehouseType


class CreateWarehouseInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateWarehouseCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=MANAGE_WAREHOUSES,
            org_unit_id=command.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        # Кросс-модульных FK нет, поэтому существование орг-единицы проверяет
        # приложение.
        if not await self._business_api.org_unit_exists(command.org_unit_id):
            raise OrgUnitNotFoundError(command.org_unit_id)

        if await self._warehouse_repository.get_by_code(command.code) is not None:
            raise WarehouseCodeAlreadyExistsError(command.code)

        warehouse = Warehouse.create(
            org_unit_id=command.org_unit_id,
            code=command.code,
            name=command.name,
            type=command.type,
        )

        await self._warehouse_repository.add(warehouse)
        await self._transaction_manager.commit()

        return warehouse.id
