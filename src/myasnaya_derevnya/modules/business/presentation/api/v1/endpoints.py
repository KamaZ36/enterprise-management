from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.business.application.interactors.create_org_unit import (
    CreateOrgUnitCommand,
    CreateOrgUnitInteractor,
)
from myasnaya_derevnya.modules.business.application.interactors.list_org_units import (
    ListOrgUnitsInteractor,
)
from myasnaya_derevnya.modules.business.presentation.api.v1.schemas import (
    CreateOrgUnitSchema,
    OrgUnitSchema,
)

router = APIRouter(prefix="/api", tags=["Структурные подразделения"])


@router.post("/org-unit", description="Создать структурную единицу")
async def create_org_unit(request: Request, data: CreateOrgUnitSchema) -> JSONResponse:
    command = CreateOrgUnitCommand(
        parent_id=data.parent_id,
        type=data.type,
        code=data.code,
        name=data.name,
        address=data.address,
        phone_number=data.phone_number,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateOrgUnitInteractor)
        org_unit_id = await interactor(command)

    return JSONResponse(status_code=201, content={"org_unit_id": str(org_unit_id)})


@router.get(
    "/org-unit",
    response_model=list[OrgUnitSchema],
    description="Список организационных единиц",
)
async def list_org_units(request: Request) -> list[OrgUnitSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListOrgUnitsInteractor)
        items = await interactor()

    return [OrgUnitSchema.from_dto(item) for item in items]
