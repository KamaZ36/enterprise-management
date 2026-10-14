from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem
from myasnaya_derevnya.modules.business.domain.permissions import ORG_UNIT_READ
from myasnaya_derevnya.modules.business.infrastructure.readers.org_unit.base import (
    OrgUnitReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ListOrgUnitsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        org_unit_reader: OrgUnitReader,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._org_unit_reader = org_unit_reader
        self._staff_api = staff_api

    async def __call__(self) -> list[OrgUnitListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        scope = await self._staff_api.scope_for(
            user_id=current_user_id, permission=ORG_UNIT_READ
        )
        if scope.is_empty():
            raise ForbiddenError()

        return [
            item for item in await self._org_unit_reader.list() if scope.covers(item.id)
        ]
