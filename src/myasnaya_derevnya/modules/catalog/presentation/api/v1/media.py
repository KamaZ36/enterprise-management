from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.catalog.application.interactors.upload_image import (
    UploadImageCommand,
    UploadImageInteractor,
)
from myasnaya_derevnya.modules.catalog.presentation.api.v1.schemas import (
    UploadedImageSchema,
)

router = APIRouter(prefix="/api/catalog", tags=["Catalog Module"])


@router.post(
    "/images",
    response_model=UploadedImageSchema,
    status_code=201,
    description="Загрузить изображение (сжимаем и пересохраняем в WebP)",
)
async def upload_image(
    request: Request, file: Annotated[UploadFile, File()]
) -> UploadedImageSchema:
    data = await file.read()

    async with container(context={Request: request}) as context:
        interactor = await context.get(UploadImageInteractor)
        uploaded = await interactor(UploadImageCommand(data=data))

    return UploadedImageSchema(
        url=uploaded.url,
        width=uploaded.width,
        height=uploaded.height,
        size_bytes=uploaded.size_bytes,
    )
