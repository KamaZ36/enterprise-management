from dataclasses import dataclass, replace
from decimal import Decimal
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
class GetBalanceQuery:
    org_unit_id: UUID
    nomenclature_id: UUID


class GetBalanceInteractor:
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

    async def __call__(self, query: GetBalanceQuery) -> BalanceListItem:
        current_user_id = await self._identity_provider.get_current_user_id()

        location = await self._business_api.stock_location(query.org_unit_id)
        if location is None:
            raise LocationNotFoundError(query.org_unit_id)

        cost_visible = await self._check_access(current_user_id, location.id)

        item = await self._balance_reader.get(
            query.org_unit_id, query.nomenclature_id, with_cost=cost_visible
        )
        if item is None:
            item = BalanceListItem(
                org_unit_id=query.org_unit_id,
                nomenclature_id=query.nomenclature_id,
                quantity=Decimal(0),
                average_unit_cost=Decimal(0) if cost_visible else None,
                total_value_kopecks=0 if cost_visible else None,
            )

        names = await self._catalog_api.nomenclature_names({item.nomenclature_id})

        return replace(item, nomenclature_name=names.get(item.nomenclature_id))

    async def _check_access(self, user_id: UUID, org_unit_id: UUID) -> bool:
        allowed = await self._staff_api.can(
            user_id=user_id, permission=READ_BALANCES, org_unit_id=org_unit_id
        )
        if not allowed:
            raise ForbiddenError()

        return await self._staff_api.can(
            user_id=user_id, permission=READ_COSTS, org_unit_id=org_unit_id
        )
