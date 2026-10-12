from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import (
    CategoryAlreadyExists,
    CategoryNotFound,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import UPDATE_CATEGORY
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.base import (
    CategoryRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class UpdateCategoryCommand:
    category_id: UUID
    name: str


class UpdateCategoryInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        category_repository: CategoryRepository,
        transaction_manager: TransactionManager,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._category_repository = category_repository
        self._transaction_manager = transaction_manager
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, command: UpdateCategoryCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        if not await self._staff_api.can(
            user_id=current_user_id,
            permission=UPDATE_CATEGORY,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        category = await self._category_repository.get_by_id(command.category_id)
        if category is None:
            raise CategoryNotFound(command.category_id)

        name = command.name.strip()
        if name == category.name:
            return

        if await self._category_repository.check_exists_by_name(name):
            raise CategoryAlreadyExists(name)

        category.rename(name)

        await self._category_repository.save(category)
        await self._transaction_manager.commit()
