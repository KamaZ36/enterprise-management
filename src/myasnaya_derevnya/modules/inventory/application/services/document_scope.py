from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_DOCUMENTS
from myasnaya_derevnya.modules.inventory.infrastructure.readers.warehouse.base import (
    WarehouseReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class DocumentScope:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        warehouse_reader: WarehouseReader,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._warehouse_reader = warehouse_reader
        self._staff_api = staff_api

    async def visible_warehouse_ids(
        self, requested: UUID | None = None
    ) -> list[UUID] | None:
        allowed = await self._allowed_warehouse_ids()

        if allowed is None:
            return None if requested is None else [requested]

        if requested is None:
            return sorted(allowed)

        if requested not in allowed:
            raise ForbiddenError()

        return [requested]

    async def ensure_can_read(self, org_unit_ids: Iterable[UUID | None]) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        for org_unit_id in org_unit_ids:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=READ_DOCUMENTS,
                org_unit_id=org_unit_id,
            )
            if allowed:
                return

        raise ForbiddenError()

    async def _allowed_warehouse_ids(self) -> frozenset[UUID] | None:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=READ_DOCUMENTS
        )

        if scope.is_empty():
            raise ForbiddenError()

        if scope.is_company_wide:
            return None

        warehouses = await self._warehouse_reader.list_all()

        return frozenset(
            warehouse.id
            for warehouse in warehouses
            if scope.covers(warehouse.org_unit_id)
        )
