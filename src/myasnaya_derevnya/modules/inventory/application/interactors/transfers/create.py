from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.application.commands import (
    TransferLineCommand,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import Warehouse
from myasnaya_derevnya.modules.inventory.domain.errors import WarehouseNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateTransferCommand:
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    occurred_at: datetime
    lines: list[TransferLineCommand]
    comment: str | None = None


class CreateTransferInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        transfer_repository: TransferRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._transfer_repository = transfer_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateTransferCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()

        from_warehouse = await self._warehouse_repository.get_by_id(
            command.from_warehouse_id
        )
        if from_warehouse is None:
            raise WarehouseNotFoundError(command.from_warehouse_id)

        to_warehouse = await self._warehouse_repository.get_by_id(
            command.to_warehouse_id
        )
        if to_warehouse is None:
            raise WarehouseNotFoundError(command.to_warehouse_id)

        await self._ensure_allowed(current_user_id, (from_warehouse, to_warehouse))

        transfer = Transfer.create(
            from_warehouse_id=command.from_warehouse_id,
            to_warehouse_id=command.to_warehouse_id,
            occurred_at=command.occurred_at,
            created_by=current_user_id,
            comment=command.comment,
            lines=[
                TransferLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    lot_code=line.lot_code,
                )
                for line in command.lines
            ],
        )

        await self._transfer_repository.add(transfer)
        await self._transaction_manager.commit()

        return transfer.id

    async def _ensure_allowed(
        self, user_id: UUID, warehouses: tuple[Warehouse, ...]
    ) -> None:
        for warehouse in warehouses:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=CREATE_DOCUMENT,
                org_unit_id=warehouse.org_unit_id,
            )
            if not allowed:
                raise ForbiddenError()
