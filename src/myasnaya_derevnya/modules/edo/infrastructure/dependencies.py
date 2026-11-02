from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.edo.application.interactors.create_document import (
    CreateEdoDocumentInteractor,
)
from myasnaya_derevnya.modules.edo.application.interactors.list_documents import (
    ListEdoDocumentsInteractor,
)
from myasnaya_derevnya.modules.edo.infrastructure.readers.document.base import (
    EdoDocumentReader,
)
from myasnaya_derevnya.modules.edo.infrastructure.readers.document.sqlalchemy import (
    SQLAlchemyEdoDocumentReader,
)
from myasnaya_derevnya.modules.edo.infrastructure.repositories.document.base import (
    EdoDocumentRepository,
)
from myasnaya_derevnya.modules.edo.infrastructure.repositories.document.sqlalchemy import (
    SQLAlchemyEdoDocumentRepository,
)
from myasnaya_derevnya.modules.edo.presentation.edo_api import EdoAPI


class EdoDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_document_repository(
        self, session: AsyncSession
    ) -> EdoDocumentRepository:
        return SQLAlchemyEdoDocumentRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_document_reader(self, session: AsyncSession) -> EdoDocumentReader:
        return SQLAlchemyEdoDocumentReader(session)

    @provide(scope=Scope.REQUEST)
    def get_edo_api(self, document_repository: EdoDocumentRepository) -> EdoAPI:
        return EdoAPI(document_repository=document_repository)

    create_document_interactor = provide(
        CreateEdoDocumentInteractor, scope=Scope.REQUEST
    )
    list_documents_interactor = provide(
        ListEdoDocumentsInteractor, scope=Scope.REQUEST
    )
