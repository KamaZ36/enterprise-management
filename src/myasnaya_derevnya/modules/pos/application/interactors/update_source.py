import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.pos.application.dto import PosSourceItem
from myasnaya_derevnya.modules.pos.application.errors import (
    PosLocationNotFoundError,
    PosSourceNotFoundError,
)
from myasnaya_derevnya.modules.pos.domain.permissions import POS_SOURCE_MANAGE
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdatePosSourceCommand:
    source_id: UUID
    name: str | None = None
    org_unit_id: UUID | None = None
    is_active: bool | None = None


class UpdatePosSourceInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        business_api: BusinessAPI,
        source_repository: PosSourceRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._business_api = business_api
        self._source_repository = source_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdatePosSourceCommand) -> PosSourceItem:
        user_id = await self._identity_provider.get_current_user_id()

        source = await self._source_repository.get_by_id(command.source_id)
        if source is None:
            raise PosSourceNotFoundError(command.source_id)

        await self._ensure_access(user_id, source.org_unit_id)
        if command.org_unit_id is not None and command.org_unit_id != source.org_unit_id:
            await self._ensure_access(user_id, command.org_unit_id)

            location = await self._business_api.stock_location(command.org_unit_id)
            if location is None:
                raise PosLocationNotFoundError(command.org_unit_id)

        source.update(
            name=command.name,
            org_unit_id=command.org_unit_id,
            is_active=command.is_active,
        )

        await self._source_repository.save(source)
        await self._transaction_manager.commit()

        titles = await self._business_api.org_unit_titles({source.org_unit_id})

        logger.info(
            "Источник продаж DoKa изменён",
            extra={
                "source_id": str(source.id),
                "doka_org_id": source.doka_org_id,
                "is_active": source.is_active,
            },
        )

        return PosSourceItem(
            id=source.id,
            doka_org_id=source.doka_org_id,
            name=source.name,
            org_unit_id=source.org_unit_id,
            is_active=source.is_active,
            created_at=source.created_at,
            updated_at=source.updated_at,
            org_unit_name=titles.get(source.org_unit_id),
        )

    async def _ensure_access(self, user_id: UUID, org_unit_id: UUID) -> None:
        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_SOURCE_MANAGE,
            org_unit_id=org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()
