from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.application.dto import PriceListBindingItem
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_PRICE_LIST
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.base import (
    PriceListBindingRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class GetPriceListBindingQuery:
    org_unit_id: UUID


class GetPriceListBindingInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        binding_repository: PriceListBindingRepository,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._binding_repository = binding_repository
        self._staff_api = staff_api

    async def __call__(
        self, query: GetPriceListBindingQuery
    ) -> PriceListBindingItem | None:
        current_user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=READ_PRICE_LIST,
        ):
            raise ForbiddenError()

        binding = await self._binding_repository.get_by_org_unit(query.org_unit_id)

        if binding is None:
            return None

        return PriceListBindingItem(
            org_unit_id=binding.org_unit_id,
            price_list_id=binding.price_list_id,
        )
