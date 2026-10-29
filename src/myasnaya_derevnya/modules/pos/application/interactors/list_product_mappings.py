from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.pos.application.dto import PosProductMappingItem
from myasnaya_derevnya.modules.pos.application.errors import PosSourceNotFoundError
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_READ
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.base import (
    PosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPosProductMappingsQuery:
    source_id: UUID
    search: str | None = None


class ListPosProductMappingsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        catalog_api: CatalogAPI,
        source_repository: PosSourceRepository,
        product_map_repository: PosProductMapRepository,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._catalog_api = catalog_api
        self._source_repository = source_repository
        self._product_map_repository = product_map_repository

    async def __call__(
        self, query: ListPosProductMappingsQuery
    ) -> list[PosProductMappingItem]:
        user_id = await self._identity_provider.get_current_user_id()

        source = await self._source_repository.get_by_id(query.source_id)
        if source is None:
            raise PosSourceNotFoundError(query.source_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_RECEIPT_READ,
            org_unit_id=source.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        mappings = await self._product_map_repository.list_by_source(
            source.id, search=query.search
        )
        names = await self._catalog_api.nomenclature_names(
            {mapping.nomenclature_id for mapping in mappings}
        )

        return [
            PosProductMappingItem(
                id=mapping.id,
                source_id=mapping.source_id,
                doka_product_guid=mapping.doka_product_guid,
                nomenclature_id=mapping.nomenclature_id,
                unit_factor=mapping.unit_factor,
                is_active=mapping.is_active,
                created_at=mapping.created_at,
                updated_at=mapping.updated_at,
                nomenclature_name=names.get(mapping.nomenclature_id),
            )
            for mapping in mappings
        ]
