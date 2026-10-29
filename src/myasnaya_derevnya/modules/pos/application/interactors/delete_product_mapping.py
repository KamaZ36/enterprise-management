import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.pos.application.errors import (
    PosProductMappingNotFoundError,
    PosSourceNotFoundError,
)
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_MANAGE
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.base import (
    PosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeletePosProductMappingCommand:
    mapping_id: UUID


class DeletePosProductMappingInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        source_repository: PosSourceRepository,
        product_map_repository: PosProductMapRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._source_repository = source_repository
        self._product_map_repository = product_map_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: DeletePosProductMappingCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        mapping = await self._product_map_repository.get_by_id(command.mapping_id)
        if mapping is None:
            raise PosProductMappingNotFoundError(command.mapping_id)

        source = await self._source_repository.get_by_id(mapping.source_id)
        if source is None:
            raise PosSourceNotFoundError(mapping.source_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_RECEIPT_MANAGE,
            org_unit_id=source.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._product_map_repository.delete(mapping.id)
        await self._transaction_manager.commit()

        logger.info(
            "Сопоставление товара DoKa удалено",
            extra={
                "mapping_id": str(mapping.id),
                "source_id": str(mapping.source_id),
                "doka_product_guid": mapping.doka_product_guid,
            },
        )
