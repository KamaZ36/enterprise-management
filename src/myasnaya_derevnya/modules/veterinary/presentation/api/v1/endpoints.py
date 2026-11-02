from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.veterinary.application.interactors.list_documents import (
    ListVeterinaryDocumentsInteractor,
    ListVeterinaryDocumentsQuery,
)
from myasnaya_derevnya.modules.veterinary.presentation.api.v1.schemas import (
    VeterinaryDocumentListSchema,
    VeterinaryDocumentSchema,
)

router = APIRouter(prefix="/api/veterinary", tags=["Ветеринария"])


@router.get(
    "/documents",
    response_model=VeterinaryDocumentListSchema,
    description="Ветеринарные документы точки",
)
async def list_veterinary_documents(
    request: Request,
    org_unit_id: Annotated[UUID, Query()],
    search: Annotated[str | None, Query(max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VeterinaryDocumentListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListVeterinaryDocumentsInteractor)
        page = await interactor(
            ListVeterinaryDocumentsQuery(
                org_unit_id=org_unit_id,
                search=search,
                limit=limit,
                offset=offset,
            )
        )

    return VeterinaryDocumentListSchema(
        items=[
            VeterinaryDocumentSchema.from_dto(item) for item in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
