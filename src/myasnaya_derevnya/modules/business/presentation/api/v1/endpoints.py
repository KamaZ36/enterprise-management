from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.business.application.interactors.create_org_unit import (
    CreateOrgUnitCommand,
    CreateOrgUnitInteractor,
)
from myasnaya_derevnya.modules.business.application.interactors.get_cafe_list import (
    CafeListOrgUnitsInteractor,
)
from myasnaya_derevnya.modules.business.application.interactors.list_org_units import (
    ListOrgUnitsInteractor,
)
from myasnaya_derevnya.modules.business.application.interactors.update_org_unit import (
    UpdateOrgUnitCommand,
    UpdateOrgUnitInteractor,
)
from myasnaya_derevnya.modules.business.presentation.api.v1.schemas import (
    CafeOrgUnitSchema,
    CreateOrgUnitSchema,
    OrgUnitSchema,
    UpdateOrgUnitSchema,
)

router = APIRouter(prefix="/api/business", tags=["Структурные подразделения"])


@router.post("/org-units", description="Создать структурную единицу")
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
    "/org-units",
    response_model=list[OrgUnitSchema],
    description="Список организационных единиц",
)
async def list_org_units(request: Request) -> list[OrgUnitSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListOrgUnitsInteractor)
        items = await interactor()

    return [OrgUnitSchema.from_dto(item) for item in items]


@router.get(
    "/org-units/cafe",
    response_model=list[CafeOrgUnitSchema],
    description="Список активных кафе",
)
async def cafe_list_org_units(request: Request) -> list[CafeOrgUnitSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CafeListOrgUnitsInteractor)
        items = await interactor()

    return [CafeOrgUnitSchema.from_dto(item) for item in items]


@router.patch("/org-units/{org_unit_id}", description="Изменить структурную единицу")
async def update_org_unit(
    request: Request, org_unit_id: UUID, data: UpdateOrgUnitSchema
) -> JSONResponse:
    command = UpdateOrgUnitCommand(
        org_unit_id=org_unit_id,
        provided=frozenset(data.model_fields_set),
        name=data.name,
        address=data.address,
        phone_number=data.phone_number,
        is_active=data.is_active,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateOrgUnitInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})
