from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.domain.entities.price import Price
from myasnaya_derevnya.modules.catalog.domain.permissions import CREATE_PRICE
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.base import (
    PriceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreatePriceCommand:
    nomenclature_id: UUID
    price_list_id: UUID
    price: Decimal


class CreatePriceInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        price_repository: PriceRepository,
        transaction_manager: TransactionManager,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._price_repository = price_repository
        self._transaction_manager = transaction_manager
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, command: CreatePriceCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        if not await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_PRICE,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        kopecks_value = int(command.price * Decimal(100))

        price = Price.create(
            nomenclature_id=command.nomenclature_id,
            price_list_id=command.price_list_id,
            value=kopecks_value,
        )

        await self._price_repository.add(price)
        await self._transaction_manager.commit()

        return price.id
