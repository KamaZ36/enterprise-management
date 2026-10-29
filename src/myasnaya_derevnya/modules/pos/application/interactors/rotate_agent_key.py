import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.pos.application.dto import PosAgentKey
from myasnaya_derevnya.modules.pos.application.errors import (
    PosAgentNotFoundError,
    PosSourceNotFoundError,
)
from myasnaya_derevnya.modules.pos.application.mappers import agent_item
from myasnaya_derevnya.modules.pos.domain.permissions import POS_SOURCE_MANAGE
from myasnaya_derevnya.modules.pos.domain.value_objects.api_key import (
    api_key_prefix,
    generate_api_key,
    hash_api_key,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RotatePosAgentKeyCommand:
    agent_id: UUID


class RotatePosAgentKeyInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        source_repository: PosSourceRepository,
        agent_repository: PosAgentRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._source_repository = source_repository
        self._agent_repository = agent_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: RotatePosAgentKeyCommand) -> PosAgentKey:
        user_id = await self._identity_provider.get_current_user_id()

        agent = await self._agent_repository.get_by_id(command.agent_id)
        if agent is None:
            raise PosAgentNotFoundError(command.agent_id)

        source = await self._source_repository.get_by_id(agent.source_id)
        if source is None:
            raise PosSourceNotFoundError(agent.source_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_SOURCE_MANAGE,
            org_unit_id=source.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        raw_key = generate_api_key()
        agent.rotate_key(
            api_key_hash=hash_api_key(raw_key),
            api_key_prefix=api_key_prefix(raw_key),
        )

        await self._agent_repository.save(agent)
        await self._transaction_manager.commit()

        logger.info(
            "Ключ агента DoKa перевыпущен",
            extra={
                "agent_id": str(agent.id),
                "source_id": str(agent.source_id),
            },
        )

        return PosAgentKey(
            agent=agent_item(agent),
            api_key=raw_key,
            api_key_prefix=agent.api_key_prefix,
        )
