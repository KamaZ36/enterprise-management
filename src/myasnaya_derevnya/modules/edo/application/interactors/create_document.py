import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.edo.domain.entities.edo_document import EdoDocument
from myasnaya_derevnya.modules.edo.domain.errors import EdoLocationNotFoundError
from myasnaya_derevnya.modules.edo.domain.permissions import MANAGE_DOCUMENTS
from myasnaya_derevnya.modules.edo.infrastructure.repositories.document.base import (
    EdoDocumentRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreateEdoDocumentCommand:
    org_unit_id: UUID
    number: str
    external_id: str | None = None
    doc_date: date | None = None
    supplier_name: str | None = None
    supplier_inn: str | None = None
    delivery_address: str | None = None
    comment: str | None = None


class CreateEdoDocumentInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        document_repository: EdoDocumentRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._staff_api = staff_api
        self._document_repository = document_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateEdoDocumentCommand) -> UUID:
        user_id = await self._identity_provider.get_current_user_id()

        location = await self._business_api.stock_location(command.org_unit_id)
        if location is None:
            raise EdoLocationNotFoundError(command.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=MANAGE_DOCUMENTS,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        document = EdoDocument.create(
            org_unit_id=command.org_unit_id,
            number=command.number,
            external_id=command.external_id,
            doc_date=command.doc_date,
            supplier_name=command.supplier_name,
            supplier_inn=command.supplier_inn,
            delivery_address=command.delivery_address,
            comment=command.comment,
            created_by=user_id,
        )
        await self._document_repository.add(document)
        await self._transaction_manager.commit()

        logger.info(
            "Зарегистрирован входящий документ ЭДО",
            extra={
                "edo_document_id": str(document.id),
                "org_unit_id": str(command.org_unit_id),
            },
        )

        return document.id
