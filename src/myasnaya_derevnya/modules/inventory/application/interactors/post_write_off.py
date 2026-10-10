from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
from myasnaya_derevnya.modules.inventory.application.services.posting_preconditions import (
    PostingPreconditions,
)
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    WriteOffNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class PostWriteOffCommand:
    write_off_id: UUID


class PostWriteOffInteractor:
    """Проведение списания: себестоимость считает журнал по средней."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        write_off_repository: WriteOffRepository,
        warehouse_repository: WarehouseRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._write_off_repository = write_off_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostWriteOffCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        write_off = await self._write_off_repository.get_by_id(command.write_off_id)
        if write_off is None:
            raise WriteOffNotFoundError(command.write_off_id)
        if not write_off.is_draft:
            raise DocumentAlreadyPostedError(write_off.id)

        lines = write_off.lines
        warehouse = await self._preconditions.ensure_ready(
            warehouse_id=write_off.warehouse_id,
            nomenclature_ids=[line.nomenclature_id for line in lines],
        )

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        lot_ids = await self._resolve_lots(write_off)

        async with self._ledger.posting(
            document_type=DocumentType.WRITE_OFF,
            document_id=write_off.id,
            warehouse_id=write_off.warehouse_id,
            occurred_at=write_off.occurred_at,
            posted_by=current_user_id,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (write_off.warehouse_id, line.nomenclature_id) for line in lines
                ],
                lot_keys=[
                    (write_off.warehouse_id, line.nomenclature_id, lot_id)
                    for line, lot_id in zip(lines, lot_ids, strict=True)
                    if lot_id is not None
                ],
            )

            for line, lot_id in zip(lines, lot_ids, strict=True):
                await posting.issue(
                    warehouse_id=write_off.warehouse_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    movement_type=MovementType.WRITE_OFF,
                    lot_id=lot_id,
                )

        write_off.post()
        await self._write_off_repository.save(write_off)
        await self._transaction_manager.commit()

    async def _resolve_lots(self, write_off) -> list[UUID | None]:
        """Списание только находит существующие партии."""
        lot_ids: list[UUID | None] = []

        for line in write_off.lines:
            if line.lot_id is not None:
                lot_ids.append(line.lot_id)
                continue

            if not line.lot_code:
                lot_ids.append(None)
                continue

            lot_ids.append(
                await self._lot_resolver.require(
                    nomenclature_id=line.nomenclature_id,
                    lot_code=line.lot_code,
                )
            )

        return lot_ids
