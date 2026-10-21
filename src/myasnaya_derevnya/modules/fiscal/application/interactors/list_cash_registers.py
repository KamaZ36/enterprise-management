from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.fiscal.application.dto import CashRegisterListItem
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_READ
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.base import (
    CashRegisterReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class ListCashRegistersQuery:
    org_unit_id: UUID | None = None
    at: datetime | None = None


class ListCashRegistersInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        cash_register_reader: CashRegisterReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._cash_register_reader = cash_register_reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(
        self, query: ListCashRegistersQuery
    ) -> list[CashRegisterListItem]:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=CASH_REGISTER_READ
        )

        if scope.is_empty():
            raise ForbiddenError()

        items = await self._cash_register_reader.list(
            org_unit_id=query.org_unit_id,
            at=query.at or get_datetime_utc(),
        )

        if not scope.is_company_wide:
            items = [
                item
                for item in items
                if item.org_unit_id is not None and scope.covers(item.org_unit_id)
            ]

        org_unit_ids = {
            item.org_unit_id for item in items if item.org_unit_id is not None
        }
        titles = await self._business_api.org_unit_titles(org_unit_ids)

        return [
            replace(item, org_unit_name=titles.get(item.org_unit_id))
            for item in items
        ]
