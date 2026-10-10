from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.dto import CategoryListItem
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_CATEGORY
from myasnaya_derevnya.modules.catalog.infrastructure.readers.category.base import (
    CategoryReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListCategoriesQuery:
    search: str | None = None

    def normalized(self) -> ListCategoriesQuery:
        search = self.search.strip() if self.search else None

        return ListCategoriesQuery(search=search or None)


class ListCategoriesInteractor:
    """Справочник категорий: нужен интерфейсу для выбора и дерева."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        category_reader: CategoryReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._category_reader = category_reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, query: ListCategoriesQuery) -> list[CategoryListItem]:
        params = query.normalized()

        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_CATEGORY,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        return await self._category_reader.list(search=params.search)
