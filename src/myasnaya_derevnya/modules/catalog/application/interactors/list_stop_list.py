from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.dto import StopListItem
from myasnaya_derevnya.modules.catalog.application.errors import (
    StopListLocationNotFound,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_STOP_LIST
from myasnaya_derevnya.modules.catalog.infrastructure.readers.stop_list.base import (
    StopListReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListStopListQuery:
    org_unit_id: UUID


class ListStopListInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        stop_list_reader: StopListReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._staff_api = staff_api
        self._stop_list_reader = stop_list_reader

    async def __call__(self, query: ListStopListQuery) -> list[StopListItem]:
        user_id = await self._identity_provider.get_current_user_id()

        location = await self._business_api.stock_location(query.org_unit_id)
        if location is None:
            raise StopListLocationNotFound(query.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=READ_STOP_LIST,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        return await self._stop_list_reader.list_by_org_unit(query.org_unit_id)
