from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_DOCUMENTS
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class DocumentScope:
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
        allowed = await self._allowed_org_unit_ids()

        if allowed is None:
            return None if requested is None else [requested]

        if requested is None:
            return sorted(allowed)

        if requested not in allowed:
            raise ForbiddenError()

        return [requested]

    async def ensure_can_read(self, org_unit_ids: Iterable[UUID | None]) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        for org_unit_id in org_unit_ids:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=READ_DOCUMENTS,
                org_unit_id=org_unit_id,
            )
            if allowed:
                return

        raise ForbiddenError()

    async def _allowed_org_unit_ids(self) -> frozenset[UUID] | None:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=READ_DOCUMENTS
        )

        if scope.is_empty():
            raise ForbiddenError()

        if scope.is_company_wide:
            return None

        locations = await self._business_api.stock_locations()

        return frozenset(
            location.id for location in locations if scope.covers(location.id)
        )
