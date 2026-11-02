from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.veterinary.application.interactors.list_documents import (
    ListVeterinaryDocumentsInteractor,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.readers.veterinary_document.base import (
    VeterinaryDocumentReader,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.readers.veterinary_document.sqlalchemy import (
    SQLAlchemyVeterinaryDocumentReader,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.repositories.veterinary_document.base import (
    VeterinaryDocumentRepository,
)
from myasnaya_derevnya.modules.veterinary.infrastructure.repositories.veterinary_document.sqlalchemy import (
    SQLAlchemyVeterinaryDocumentRepository,
)
from myasnaya_derevnya.modules.veterinary.presentation.veterinary_api import (
    VeterinaryAPI,
)


class VeterinaryDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_document_repository(
        self, session: AsyncSession
    ) -> VeterinaryDocumentRepository:
        return SQLAlchemyVeterinaryDocumentRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_document_reader(
        self, session: AsyncSession
    ) -> VeterinaryDocumentReader:
        return SQLAlchemyVeterinaryDocumentReader(session)

    @provide(scope=Scope.REQUEST)
    def get_veterinary_api(
        self, document_repository: VeterinaryDocumentRepository
    ) -> VeterinaryAPI:
        return VeterinaryAPI(document_repository=document_repository)

    list_documents_interactor = provide(
        ListVeterinaryDocumentsInteractor, scope=Scope.REQUEST
    )
