from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import LotBalanceListItem
from myasnaya_derevnya.modules.inventory.domain.errors import WarehouseNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.lot_balance.base import (
    LotBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListLotBalancesQuery:
    warehouse_id: UUID
    search: str | None = None
    expiring_before: date | None = None
    include_empty: bool = False


class ListLotBalancesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        lot_balance_reader: LotBalanceReader,
        catalog_api: CatalogAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._lot_balance_reader = lot_balance_reader
        self._catalog_api = catalog_api
        self._staff_api = staff_api

    async def __call__(
        self, query: ListLotBalancesQuery
    ) -> list[LotBalanceListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        warehouse = await self._warehouse_repository.get_by_id(query.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(query.warehouse_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_BALANCES,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        cost_visible = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_COSTS,
            org_unit_id=warehouse.org_unit_id,
        )

        items = await self._lot_balance_reader.list_by_warehouse(
            query.warehouse_id,
            with_cost=cost_visible,
            include_empty=query.include_empty,
            expiring_before=query.expiring_before,
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
                or needle in item.lot_code.lower()
            ]

        return result
