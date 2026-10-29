from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.pos.application.dto import PosUnmappedProductItem
from myasnaya_derevnya.modules.pos.application.errors import PosSourceNotFoundError
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_READ
from myasnaya_derevnya.modules.pos.infrastructure.readers.product_map.base import (
    PosProductMapReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPosUnmappedProductsQuery:
    source_id: UUID
    limit: int = 200


class ListPosUnmappedProductsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        source_repository: PosSourceRepository,
        product_map_reader: PosProductMapReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._source_repository = source_repository
        self._product_map_reader = product_map_reader

    async def __call__(
        self, query: ListPosUnmappedProductsQuery
    ) -> list[PosUnmappedProductItem]:
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

        return await self._product_map_reader.unmapped_products(
            source.id, limit=query.limit
        )
