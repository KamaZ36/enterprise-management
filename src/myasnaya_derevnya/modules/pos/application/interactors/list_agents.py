from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.pos.application.dto import PosAgentItem
from myasnaya_derevnya.modules.pos.application.errors import PosSourceNotFoundError
from myasnaya_derevnya.modules.pos.application.mappers import agent_item
from myasnaya_derevnya.modules.pos.domain.permissions import POS_SOURCE_READ
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPosAgentsQuery:
    source_id: UUID


class ListPosAgentsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        source_repository: PosSourceRepository,
        agent_repository: PosAgentRepository,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._source_repository = source_repository
        self._agent_repository = agent_repository

    async def __call__(self, query: ListPosAgentsQuery) -> list[PosAgentItem]:
        user_id = await self._identity_provider.get_current_user_id()

        source = await self._source_repository.get_by_id(query.source_id)
        if source is None:
            raise PosSourceNotFoundError(query.source_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_SOURCE_READ,
            org_unit_id=source.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        agents = await self._agent_repository.list_by_source(source.id)

        return [agent_item(agent) for agent in agents]
