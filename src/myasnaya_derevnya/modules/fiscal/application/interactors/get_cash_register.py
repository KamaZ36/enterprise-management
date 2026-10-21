from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.fiscal.application.dto import CashRegisterDetail
from myasnaya_derevnya.modules.fiscal.application.errors import CashRegisterNotFound
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_READ
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.base import (
    CashRegisterReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class GetCashRegisterQuery:
    cash_register_id: UUID


class GetCashRegisterInteractor:
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

    async def __call__(self, query: GetCashRegisterQuery) -> CashRegisterDetail:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=CASH_REGISTER_READ
        )

        if scope.is_empty():
            raise ForbiddenError()

        detail = await self._cash_register_reader.get(query.cash_register_id)
        if detail is None:
            raise CashRegisterNotFound(query.cash_register_id)

        if not scope.is_company_wide and (
            detail.org_unit_id is None or not scope.covers(detail.org_unit_id)
        ):
            raise ForbiddenError()

        org_unit_ids = {binding.org_unit_id for binding in detail.bindings}
        titles = await self._business_api.org_unit_titles(org_unit_ids)
        bindings = tuple(
            replace(binding, org_unit_name=titles.get(binding.org_unit_id))
            for binding in detail.bindings
        )

        return replace(
            detail,
            org_unit_name=titles.get(detail.org_unit_id),
            bindings=bindings,
        )
