from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.edo.application.interactors.create_document import (
    CreateEdoDocumentCommand,
    CreateEdoDocumentInteractor,
)
from myasnaya_derevnya.modules.edo.application.interactors.list_documents import (
    ListEdoDocumentsInteractor,
    ListEdoDocumentsQuery,
)
from myasnaya_derevnya.modules.edo.presentation.api.v1.schemas import (
    CreateEdoDocumentSchema,
    EdoDocumentListSchema,
    EdoDocumentSchema,
)

router = APIRouter(prefix="/api/edo", tags=["ЭДО"])


@router.post(
    "/documents",
    description="Зарегистрировать входящий документ ЭДО вручную",
    status_code=201,
)
async def create_edo_document(
    request: Request, data: CreateEdoDocumentSchema
) -> JSONResponse:
    command = CreateEdoDocumentCommand(
        org_unit_id=data.org_unit_id,
        number=data.number,
        external_id=data.external_id,
        doc_date=data.doc_date,
        supplier_name=data.supplier_name,
        supplier_inn=data.supplier_inn,
        delivery_address=data.delivery_address,
        comment=data.comment,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateEdoDocumentInteractor)
        document_id = await interactor(command)

    return JSONResponse(
        status_code=201, content={"document_id": str(document_id)}
    )


@router.get(
    "/documents",
    response_model=EdoDocumentListSchema,
    description="Входящие документы ЭДО точки",
)
async def list_edo_documents(
    request: Request,
    org_unit_id: Annotated[UUID, Query()],
    search: Annotated[str | None, Query(max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EdoDocumentListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListEdoDocumentsInteractor)
        items, total = await interactor(
            ListEdoDocumentsQuery(
                org_unit_id=org_unit_id,
                search=search,
                limit=limit,
                offset=offset,
            )
        )

    return EdoDocumentListSchema(
        items=[EdoDocumentSchema.from_dto(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
