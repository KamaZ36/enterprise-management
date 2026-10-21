from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.fiscal.application.dto import StockLocationOption
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_READ
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ListStockLocationsInteractor:
    """Точки, к которым можно привязать кассу."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self) -> list[StockLocationOption]:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=CASH_REGISTER_READ
        ):
            raise ForbiddenError()

        locations = await self._business_api.stock_locations()

        return [
            StockLocationOption(
                id=location.id,
                name=location.name,
                is_active=location.is_active,
            )
            for location in locations
        ]
