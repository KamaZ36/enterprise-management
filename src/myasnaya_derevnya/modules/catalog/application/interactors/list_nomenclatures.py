from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.dto import NomenclatureListItem
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_NOMENCLATURE
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature.base import (
    NomenclatureReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True, slots=True)
class ListNomenclaturesQuery:
    search: str | None = None
    type_code: str | None = None
    category_id: UUID | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    def normalized(self) -> ListNomenclaturesQuery:
        search = self.search.strip() if self.search else None

        return ListNomenclaturesQuery(
            search=search or None,
            type_code=self.type_code,
            category_id=self.category_id,
            limit=min(max(self.limit, 1), MAX_LIMIT),
            offset=max(self.offset, 0),
        )


@dataclass(frozen=True, slots=True)
class NomenclaturePage:
    items: list[NomenclatureListItem]
    total: int
    limit: int
    offset: int


class ListNomenclaturesInteractor:
    """Список номенклатуры для интерфейса: читает через читателя, не через домен."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        nomenclature_reader: NomenclatureReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._nomenclature_reader = nomenclature_reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, query: ListNomenclaturesQuery) -> NomenclaturePage:
        page = query.normalized()

        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_NOMENCLATURE,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        items, total = await self._nomenclature_reader.list(
            search=page.search,
            type_code=page.type_code,
            category_id=page.category_id,
            limit=page.limit,
            offset=page.offset,
        )

        return NomenclaturePage(
            items=items,
            total=total,
            limit=page.limit,
            offset=page.offset,
        )
