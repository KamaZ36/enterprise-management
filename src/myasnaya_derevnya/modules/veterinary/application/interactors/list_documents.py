from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI
from myasnaya_derevnya.modules.veterinary.application.dto import VeterinaryDocumentPage
from myasnaya_derevnya.modules.veterinary.domain.permissions import READ_DOCUMENTS
from myasnaya_derevnya.modules.veterinary.infrastructure.readers.veterinary_document.base import (
    VeterinaryDocumentReader,
)


@dataclass(frozen=True, slots=True)
class ListVeterinaryDocumentsQuery:
    org_unit_id: UUID
    search: str | None = None
    limit: int = 20
    offset: int = 0


class ListVeterinaryDocumentsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        reader: VeterinaryDocumentReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._reader = reader

    async def __call__(
        self, query: ListVeterinaryDocumentsQuery
    ) -> VeterinaryDocumentPage:
        user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=READ_DOCUMENTS,
            org_unit_id=query.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        items, total = await self._reader.list(
            org_unit_id=query.org_unit_id,
            search=(query.search or "").strip() or None,
            limit=query.limit,
            offset=query.offset,
        )

        return VeterinaryDocumentPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
