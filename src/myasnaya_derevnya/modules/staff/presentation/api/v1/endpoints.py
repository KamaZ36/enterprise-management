from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.staff.application.interactors.assign_role import (
    AssignRoleCommand,
    AssignRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_credential import (
    CreateCredentialEmployeeCommand,
    CreateCredentialEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_employee import (
    CreateEmployeeCommand,
    CreateEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.role.create import (
    CreateRoleCommand,
    CreateRoleInteractor,
)
from myasnaya_derevnya.modules.staff.presentation.api.v1.schemas import (
    AssignRoleCommandSchema,
)

router = APIRouter(prefix="/api/employees", tags=["Сотрудники"])


@router.post("", description="Создать сотрудника")
async def create_employee(
    request: Request, command: CreateEmployeeCommand
) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateEmployeeInteractor)
        employee_id = await interactor(command)

    return JSONResponse(status_code=201, content={"employee_id": str(employee_id)})


@router.post("/credential", description="Создать учетные данные для сотрудника")
async def create_credential_for_employee(
    request: Request, command: CreateCredentialEmployeeCommand
) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateCredentialEmployeeInteractor)
        credentials = await interactor(command)

    return JSONResponse(status_code=201, content=credentials)


@router.post("/roles", description="Создать роль сотрудника")
async def create_employee_role(
    request: Request, command: CreateRoleCommand
) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateRoleInteractor)
        role_id = await interactor(command)

    return JSONResponse(status_code=201, content={"role_id": str(role_id)})


@router.post("/{employee_id}/roles", description="Назначить роль сотруднику")
async def assign_role(
    request: Request, employee_id: UUID, data: AssignRoleCommandSchema
) -> JSONResponse:
    command = AssignRoleCommand(
        employee_id=employee_id,
        role_id=data.role_id,
        org_unit_id=data.org_unit_id,
        include_descendants=data.include_descendants,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(AssignRoleInteractor)
        await interactor(command)

    return JSONResponse(status_code=201, content={"message": "ok!"})
