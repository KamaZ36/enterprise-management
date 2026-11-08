from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_COSTS
from myasnaya_derevnya.modules.reports.domain.permissions import READ_REPORTS
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ReportScope:
    """Какие точки пользователь может видеть в отчётах."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._staff_api = staff_api

    async def visible_org_unit_ids(
        self, requested: UUID | None = None
    ) -> list[UUID] | None:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=READ_REPORTS
        )

        if scope.is_empty():
            raise ForbiddenError()

        if scope.is_company_wide:
            return None if requested is None else [requested]

        locations = await self._business_api.stock_locations()
        allowed = frozenset(
            location.id for location in locations if scope.covers(location.id)
        )

        if requested is None:
            return sorted(allowed)

        if requested not in allowed:
            raise ForbiddenError()

        return [requested]

    async def can_see_costs(self) -> bool:
        user_id = await self._identity_provider.get_current_user_id()

        return await self._staff_api.can_anywhere(
            user_id=user_id, permission=READ_COSTS
        )
