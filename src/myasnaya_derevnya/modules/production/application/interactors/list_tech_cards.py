from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.production.application.dto import TechCardPage
from myasnaya_derevnya.modules.production.domain.permissions import READ_TECH_CARDS
from myasnaya_derevnya.modules.production.infrastructure.readers.tech_card.base import (
    TechCardReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListTechCardsQuery:
    search: str | None = None
    limit: int = 50
    offset: int = 0


class ListTechCardsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        tech_card_reader: TechCardReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._tech_card_reader = tech_card_reader

    async def __call__(self, query: ListTechCardsQuery) -> TechCardPage:
        user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=user_id, permission=READ_TECH_CARDS
        )
        if not allowed:
            raise ForbiddenError()

        search = query.search.strip() if query.search else None
        items, total = await self._tech_card_reader.list(
            search=search or None,
            limit=query.limit,
            offset=query.offset,
        )

        return TechCardPage(items=items, total=total)
