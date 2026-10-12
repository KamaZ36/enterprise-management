from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.dto import WriteOffListItem
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_DOCUMENTS
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.base import (
    WriteOffReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListWriteOffsQuery:
    warehouse_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class WriteOffPage:
    items: list[WriteOffListItem]
    total: int
    limit: int
    offset: int


class ListWriteOffsInteractor:
    """Журнал списаний: просрочка, брак, недостача."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        write_off_reader: WriteOffReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._write_off_reader = write_off_reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, query: ListWriteOffsQuery) -> WriteOffPage:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_DOCUMENTS,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        items, total = await self._write_off_reader.list(
            warehouse_id=query.warehouse_id,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return WriteOffPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
