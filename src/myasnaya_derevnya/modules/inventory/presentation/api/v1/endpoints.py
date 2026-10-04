from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.inventory.application.interactors.create_location import (
    CreateLocationCommand,
    CreateLocationInteractor,
)
from myasnaya_derevnya.modules.inventory.presentation.api.v1.schemas import (
    CreateLocationSchema,
)

router = APIRouter(prefix="/api", tags=["Inventory"])


@router.post("/locations", description="Создать локацию бизнеса")
async def create_location(request: Request, data: CreateLocationSchema) -> JSONResponse:
    command = CreateLocationCommand(
        name=data.name, location_type=data.location_type, address=data.address
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateLocationInteractor)
        location_id = await interactor(command)

    return JSONResponse(status_code=201, content={"location_id": str(location_id)})
