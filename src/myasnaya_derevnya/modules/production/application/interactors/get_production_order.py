from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.production.application.dto import (
    ProductionOrderDetail,
    ProductionOrderLineItem,
    ProductionOrderLotItem,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionLocationNotFoundError,
    ProductionOrderNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import READ_ORDERS
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class GetProductionOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        inventory_api: InventoryAPI,
        order_repository: ProductionOrderRepository,
        catalog_api: CatalogAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._inventory_api = inventory_api
        self._order_repository = order_repository
        self._catalog_api = catalog_api

    async def __call__(self, order_id: UUID) -> ProductionOrderDetail:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(order_id)
        if order is None:
            raise ProductionOrderNotFoundError(order_id)

        location = await self._inventory_api.get_location(order.org_unit_id)
        if location is None:
            raise ProductionLocationNotFoundError(order.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=READ_ORDERS,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        names = await self._catalog_api.nomenclature_names(
            [
                line.nomenclature_id
                for line in order.lines
                if line.nomenclature_id is not None
            ]
        )

        component_nomenclature_ids = [
            line.nomenclature_id
            for line in order.components
            if line.nomenclature_id is not None
        ]
        available = await self._inventory_api.available_lots(
            org_unit_id=order.org_unit_id,
            nomenclature_ids=component_nomenclature_ids,
        )
        available_by_nomenclature: dict[UUID, list[ProductionOrderLotItem]] = {}
        for lot in available:
            available_by_nomenclature.setdefault(lot.nomenclature_id, []).append(
                ProductionOrderLotItem(
                    id=lot.id,
                    code=lot.code,
                    quantity=lot.quantity,
                    expires_at=lot.expires_at,
                )
            )

        component_line_ids = {line.id for line in order.components}
        lot_codes = await self._inventory_api.lot_codes(
            line.lot_id for line in order.lines if line.lot_id is not None
        )

        return ProductionOrderDetail(
            id=order.id,
            org_unit_id=order.org_unit_id,
            location_name=location.name,
            tech_card_id=order.tech_card_id,
            tech_card_code=order.tech_card_code,
            tech_card_version=order.tech_card_version,
            status=order.status,
            occurred_at=order.occurred_at,
            batch_count=order.batch_count,
            created_at=order.created_at,
            comment=order.comment,
            posted_at=order.posted_at,
            vetis_status=order.vetis_status.value,
            vetis_operation_id=order.vetis_operation_id,
            vetis_no_vsd_reason=order.vetis_no_vsd_reason,
            vetis_entered_at=order.vetis_entered_at,
            lines=[
                ProductionOrderLineItem(
                    id=line.id,
                    role=line.role,
                    planned_quantity=line.planned_quantity,
                    actual_quantity=line.actual_quantity,
                    nomenclature_id=line.nomenclature_id,
                    nomenclature_name=names.get(line.nomenclature_id)
                    if line.nomenclature_id
                    else None,
                    lot_id=line.lot_id,
                    lot_code=lot_codes.get(line.lot_id)
                    if line.lot_id is not None
                    else None,
                    expires_at=line.expires_at,
                    vetis_production_vsd_number=line.vetis_production_vsd_number,
                    vetis_production_vsd_guid=line.vetis_production_vsd_guid,
                    vetis_batch_id=line.vetis_batch_id,
                    available_lots=tuple(
                        available_by_nomenclature.get(line.nomenclature_id, ())
                    )
                    if line.id in component_line_ids
                    and line.nomenclature_id is not None
                    else (),
                    loss_kind=line.loss_kind,
                    output_kind=line.output_kind,
                    cost=line.cost_kopecks,
                )
                for line in order.lines
            ],
        )
