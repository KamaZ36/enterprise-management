import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.domain.errors import (
    NotSoldAtPointError,
    OrderNotFoundError,
)
from myasnaya_derevnya.modules.sales.domain.permissions import UPDATE_ORDER
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateOrderLineCommand:
    nomenclature_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class UpdateOrderCommand:
    order_id: UUID
    lines: tuple[UpdateOrderLineCommand, ...]
    planned_at: datetime | None = None
    comment: str | None = None


class UpdateOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_repository: OrderRepository,
        catalog_api: CatalogAPI,
        order_access: OrderAccess,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_repository = order_repository
        self._catalog_api = catalog_api
        self._order_access = order_access
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateOrderCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)
        if order is None:
            raise OrderNotFoundError(command.order_id)

        await self._order_access.ensure_is_staff(
            user_id=user_id, order=order, permission=UPDATE_ORDER
        )

        prices = await self._catalog_api.prices_for_point(
            order.org_unit_id,
            [line.nomenclature_id for line in command.lines],
        )

        resolved: list[tuple[UUID, Decimal, int]] = []
        for line in command.lines:
            price = prices.get(line.nomenclature_id)
            if price is None:
                raise NotSoldAtPointError(line.nomenclature_id)

            resolved.append((line.nomenclature_id, line.quantity, price))

        order.revise(
            lines=resolved,
            planned_at=command.planned_at,
            comment=command.comment,
        )

        await self._order_repository.save(order)
        await self._transaction_manager.commit()

        logger.info("Заказ изменён", extra={"order_id": str(order.id)})
