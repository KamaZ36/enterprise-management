
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.dto import LocationListItem
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    CREATE_DOCUMENT,
    POST_DOCUMENT,
    READ_BALANCES,
    READ_DOCUMENTS,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

_ANY_PERMISSION = (READ_BALANCES, READ_DOCUMENTS, CREATE_DOCUMENT, POST_DOCUMENT)


class ListLocationsInteractor:
    """Список складских локаций (подразделений) для выбора в интерфейсе."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self) -> list[LocationListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        allowed = False
        for permission in _ANY_PERMISSION:
            if await self._staff_api.can_anywhere(current_user_id, permission):
                allowed = True
                break

        if not allowed:
            raise ForbiddenError()

        locations = await self._business_api.stock_locations()

        return [
            LocationListItem(
                id=location.id,
                name=location.name,
                is_active=location.is_active,
            )
            for location in locations
        ]
