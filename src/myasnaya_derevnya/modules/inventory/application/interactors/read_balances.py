from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.domain.entities.stock_balance import (
    StockBalance,
)
from myasnaya_derevnya.modules.inventory.domain.errors import WarehouseNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class BalanceView:
    """Остаток и признак, можно ли показывать стоимость."""

    balance: StockBalance
    cost_visible: bool


@dataclass(frozen=True, slots=True)
class GetBalanceQuery:
    warehouse_id: UUID
    nomenclature_id: UUID


class GetBalanceInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        balance_repository: StockBalanceRepository,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._balance_repository = balance_repository
        self._staff_api = staff_api

    async def __call__(self, query: GetBalanceQuery) -> BalanceView:
        current_user_id = await self._identity_provider.get_current_user_id()

        warehouse = await self._warehouse_repository.get_by_id(query.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(query.warehouse_id)

        cost_visible = await self._check_access(current_user_id, warehouse.org_unit_id)

        balance = await self._balance_repository.get(
            query.warehouse_id, query.nomenclature_id
        )
        if balance is None:
            # Пары «склад + номенклатура» может ещё не быть в балансах:
            # для вызывающего это просто нулевой остаток.
            balance = StockBalance.empty(
                warehouse_id=query.warehouse_id,
                nomenclature_id=query.nomenclature_id,
            )

        return BalanceView(balance=balance, cost_visible=cost_visible)

    async def _check_access(self, user_id: UUID, org_unit_id: UUID) -> bool:
        allowed = await self._staff_api.can(
            user_id=user_id, permission=READ_BALANCES, org_unit_id=org_unit_id
        )
        if not allowed:
            raise ForbiddenError()

        return await self._staff_api.can(
            user_id=user_id, permission=READ_COSTS, org_unit_id=org_unit_id
        )


@dataclass(frozen=True, slots=True)
class ListBalancesQuery:
    warehouse_id: UUID


class ListBalancesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_repository: WarehouseRepository,
        balance_repository: StockBalanceRepository,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_repository = warehouse_repository
        self._balance_repository = balance_repository
        self._staff_api = staff_api

    async def __call__(self, query: ListBalancesQuery) -> list[BalanceView]:
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

        balances = await self._balance_repository.list_by_warehouse(query.warehouse_id)

        return [
            BalanceView(balance=balance, cost_visible=cost_visible)
            for balance in balances
        ]
