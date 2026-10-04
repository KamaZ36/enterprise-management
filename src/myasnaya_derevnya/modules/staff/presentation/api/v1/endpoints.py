from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.staff.application.interactors.create_credential import (
    CreateCredentialEmployeeCommand,
    CreateCredentialEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_employee import (
    CreateEmployeeCommand,
    CreateEmployeeInteractor,
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
