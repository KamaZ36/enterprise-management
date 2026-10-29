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
    PosSourceAlreadyExistsError,
)
from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.domain.permissions import POS_SOURCE_MANAGE
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreatePosSourceCommand:
    doka_org_id: str
    name: str
    org_unit_id: UUID


class CreatePosSourceInteractor:
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

    async def __call__(self, command: CreatePosSourceCommand) -> PosSourceItem:
        user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_SOURCE_MANAGE,
            org_unit_id=command.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        location = await self._business_api.stock_location(command.org_unit_id)
        if location is None:
            raise PosLocationNotFoundError(command.org_unit_id)

        source = PosSource.create(
            doka_org_id=command.doka_org_id,
            name=command.name,
            org_unit_id=command.org_unit_id,
        )

        existing = await self._source_repository.get_by_doka_org_id(
            source.doka_org_id
        )
        if existing is not None:
            raise PosSourceAlreadyExistsError(source.doka_org_id)

        await self._source_repository.add(source)
        await self._transaction_manager.commit()

        logger.info(
            "Источник продаж DoKa добавлен",
            extra={
                "source_id": str(source.id),
                "doka_org_id": source.doka_org_id,
                "org_unit_id": str(source.org_unit_id),
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
            org_unit_name=location.name,
        )
