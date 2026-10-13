from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.dto import NomenclaturePriceItem
from myasnaya_derevnya.modules.catalog.application.errors import NomenclatureNotFound
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_PRICE
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.base import (
    NomenclaturePricesReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListNomenclaturePricesQuery:
    nomenclature_id: UUID


class ListNomenclaturePricesInteractor:
    """Цены позиции по всем прайс-листам: что задано, а что нет."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        nomenclature_repository: NomenclatureRepository,
        prices_reader: NomenclaturePricesReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._nomenclature_repository = nomenclature_repository
        self._prices_reader = prices_reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(
        self, query: ListNomenclaturePricesQuery
    ) -> list[NomenclaturePriceItem]:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_PRICE,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        nomenclature = await self._nomenclature_repository.get_by_id(
            query.nomenclature_id
        )
        if nomenclature is None:
            raise NomenclatureNotFound(query.nomenclature_id)

        return await self._prices_reader.list_by_nomenclature(query.nomenclature_id)
