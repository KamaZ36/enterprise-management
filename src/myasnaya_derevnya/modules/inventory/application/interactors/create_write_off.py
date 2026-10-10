from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.application.commands import (
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.domain.entities.write_off import (
    WriteOff,
    WriteOffLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import WarehouseNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateWriteOffCommand:
    warehouse_id: UUID
    occurred_at: datetime
    lines: list[WriteOffLineCommand]
    reason: str | None = None
    comment: str | None = None


class CreateWriteOffInteractor:
    """Создаёт черновик списания: просрочка, брак, недостача."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        write_off_repository: WriteOffRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._write_off_repository = write_off_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateWriteOffCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()

        warehouse = await self._warehouse_repository.get_by_id(command.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(command.warehouse_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_DOCUMENT,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        write_off = WriteOff.create(
            warehouse_id=command.warehouse_id,
            occurred_at=command.occurred_at,
            created_by=current_user_id,
            reason=command.reason,
            comment=command.comment,
            lines=[
                WriteOffLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    lot_code=line.lot_code,
                )
                for line in command.lines
            ],
        )

        await self._write_off_repository.add(write_off)
        await self._transaction_manager.commit()

        return write_off.id
