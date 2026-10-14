from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.dto import (
    PriceListEntry,
    PriceListPriceItem,
)
from myasnaya_derevnya.modules.catalog.application.errors import PriceListNotFound
from myasnaya_derevnya.modules.catalog.domain.permissions import (
    READ_PRICE,
    READ_PRICE_LIST,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.price_lists import (
    SQLAlchemyPriceListsReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPriceListsQuery:
    pass


class ListPriceListsInteractor:
    """Список прайс-листов."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        reader: SQLAlchemyPriceListsReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._reader = reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self) -> list[PriceListEntry]:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        if not await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=READ_PRICE_LIST,
        ):
            raise ForbiddenError()

        return await self._reader.list_price_lists()


@dataclass(frozen=True, slots=True)
class ListPriceListPricesQuery:
    price_list_id: UUID
    search: str | None = None
    limit: int = 50
    offset: int = 0


class ListPriceListPricesInteractor:
    """Позиции прайс-листа: у кого цена есть, а у кого нет."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        reader: SQLAlchemyPriceListsReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._reader = reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(
        self, query: ListPriceListPricesQuery
    ) -> tuple[list[PriceListPriceItem], int]:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        if not await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=READ_PRICE,
        ):
            raise ForbiddenError()

        lists = await self._reader.list_price_lists()

        if not any(item.id == query.price_list_id for item in lists):
            raise PriceListNotFound(query.price_list_id)

        return await self._reader.list_by_price_list(
            query.price_list_id,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )
