from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.pos.application.dto import PosSourceItem
from myasnaya_derevnya.modules.pos.domain.permissions import POS_SOURCE_READ
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPosSourcesQuery:
    pass


class ListPosSourcesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        business_api: BusinessAPI,
        source_repository: PosSourceRepository,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._business_api = business_api
        self._source_repository = source_repository

    async def __call__(self, query: ListPosSourcesQuery) -> list[PosSourceItem]:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=POS_SOURCE_READ
        )
        if scope.is_empty():
            raise ForbiddenError()

        sources = await self._source_repository.list_all()
        if not scope.is_company_wide:
            sources = [
                source for source in sources if scope.covers(source.org_unit_id)
            ]

        titles = await self._business_api.org_unit_titles(
            {source.org_unit_id for source in sources}
        )

        return [
            PosSourceItem(
                id=source.id,
                doka_org_id=source.doka_org_id,
                name=source.name,
                org_unit_id=source.org_unit_id,
                is_active=source.is_active,
                created_at=source.created_at,
                updated_at=source.updated_at,
                org_unit_name=titles.get(source.org_unit_id),
            )
            for source in sources
        ]
