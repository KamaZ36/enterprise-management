from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.balance.base import (
    BalanceReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListBalancesQuery:
    org_unit_id: UUID
    search: str | None = None


class ListBalancesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        balance_reader: BalanceReader,
        catalog_api: CatalogAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._balance_reader = balance_reader
        self._catalog_api = catalog_api
        self._staff_api = staff_api

    async def __call__(self, query: ListBalancesQuery) -> list[BalanceListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        location = await self._business_api.stock_location(query.org_unit_id)
        if location is None:
            raise LocationNotFoundError(query.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_BALANCES,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        cost_visible = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_COSTS,
            org_unit_id=location.id,
        )

        items = await self._balance_reader.list_by_org_unit(
            query.org_unit_id, with_cost=cost_visible
        )

        names = await self._catalog_api.nomenclature_names(
            {item.nomenclature_id for item in items}
        )

        result = [
            replace(item, nomenclature_name=names.get(item.nomenclature_id))
            for item in items
        ]

        needle = (query.search or "").strip().lower()
        if needle:
            result = [
                item
                for item in result
                if needle in (item.nomenclature_name or "").lower()
            ]

        return result
