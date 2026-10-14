from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import PriceListNotFound
from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import CREATE_PRICE_LIST
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.base import (
    PriceListRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.base import (
    PriceListBindingRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class BindPriceListCommand:
    org_unit_id: UUID
    price_list_id: UUID


class BindPriceListInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        binding_repository: PriceListBindingRepository,
        price_list_repository: PriceListRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._binding_repository = binding_repository
        self._price_list_repository = price_list_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: BindPriceListCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=CREATE_PRICE_LIST,
        )
        if not allowed:
            raise ForbiddenError()

        price_list = await self._price_list_repository.get_by_id(command.price_list_id)
        if price_list is None:
            raise PriceListNotFound(command.price_list_id)

        await self._binding_repository.save(
            PriceListBinding.create(
                org_unit_id=command.org_unit_id,
                price_list_id=command.price_list_id,
            )
        )
        await self._transaction_manager.commit()
