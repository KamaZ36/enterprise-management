from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.pos.application.dto import PosLocationItem
from myasnaya_derevnya.modules.pos.domain.permissions import (
    POS_SOURCE_MANAGE,
    POS_SOURCE_READ,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ListPosLocationsInteractor:
    """Складские локации, к которым можно привязать кассу DoKa."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._business_api = business_api

    async def __call__(self) -> list[PosLocationItem]:
        user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=user_id, permission=POS_SOURCE_READ
        ) or await self._staff_api.can_anywhere(
            user_id=user_id, permission=POS_SOURCE_MANAGE
        )
        if not allowed:
            raise ForbiddenError()

        locations = await self._business_api.stock_locations()

        return [
            PosLocationItem(
                id=location.id,
                name=location.name,
                is_active=location.is_active,
            )
            for location in locations
        ]
