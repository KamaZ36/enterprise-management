from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.organization.application.interactors.create_location import (
    CreateLocationCommand,
    CreateLocationInteractor,
)

router = APIRouter(prefix="/api/location", tags=["Локации бизнеса"])


@router.post("", description="Создать локацию")
async def create_location(
    request: Request, command: CreateLocationCommand
) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateLocationInteractor)
        await interactor(command)

    return JSONResponse(status_code=201, content={"message": "ok!"})
