from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.application.dto import PriceListEntry
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_PRICE_LIST
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.price_lists import (
    SQLAlchemyPriceListsReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPriceListsQuery:
    pass


class ListPriceListsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        reader: SQLAlchemyPriceListsReader,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._reader = reader
        self._staff_api = staff_api

    async def __call__(self) -> list[PriceListEntry]:
        current_user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=READ_PRICE_LIST,
        ):
            raise ForbiddenError()

        return await self._reader.list_price_lists()
