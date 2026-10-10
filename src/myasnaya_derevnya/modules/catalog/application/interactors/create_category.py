from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import CategoryAlreadyExists
from myasnaya_derevnya.modules.catalog.domain.entities.category import Category
from myasnaya_derevnya.modules.catalog.domain.permissions import CREATE_CATEGORY
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.base import (
    CategoryRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateCategoryCommand:
    name: str
    parent_id: UUID | None


class CreateCategoryInteractor:
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

    async def __call__(self, command: CreateCategoryCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()
        if not await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_CATEGORY,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        if await self._category_repository.check_exists_by_name(command.name):
            raise CategoryAlreadyExists(category_name=command.name)

        category = Category.create(name=command.name, parent_id=command.parent_id)

        await self._category_repository.add(category)
        await self._transaction_manager.commit()

        return category.id
