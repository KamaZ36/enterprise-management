from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import PriceListAlreadyExists
from myasnaya_derevnya.modules.catalog.domain.entities.price_list import PriceList
from myasnaya_derevnya.modules.catalog.domain.permissions import CREATE_PRICE_LIST
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.base import (
    PriceListRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreatePriceListCommand:
    name: str


class CreatePriceListInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        price_list_repository: PriceListRepository,
        transaction_manager: TransactionManager,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._price_list_repository = price_list_repository
        self._transaction_manager = transaction_manager
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, command: CreatePriceListCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        if not await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_PRICE_LIST,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        if await self._price_list_repository.check_exists_by_name(command.name):
            raise PriceListAlreadyExists(command.name)

        price_list = PriceList.create(name=command.name)

        await self._price_list_repository.add(price_list)
        await self._transaction_manager.commit()

        return price_list.id
