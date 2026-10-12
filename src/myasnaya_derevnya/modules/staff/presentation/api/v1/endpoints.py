from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
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
from myasnaya_derevnya.modules.staff.application.interactors.get_employee_by_id import (
    GetEmployeeByIdInteractor,
    GetEmployeeByIdQuery,
)
from myasnaya_derevnya.modules.staff.application.interactors.list_employee_roles import (
    ListEmployeeRolesInteractor,
    ListEmployeeRolesQuery,
)
from myasnaya_derevnya.modules.staff.application.interactors.list_employees import (
    ListEmployeesInteractor,
    ListEmployeesQuery,
)
from myasnaya_derevnya.modules.staff.application.interactors.reset_employee_password import (
    ResetEmployeePasswordCommand,
    ResetEmployeePasswordInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.revoke_role import (
    RevokeRoleCommand,
    RevokeRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.role.create import (
    CreateRoleCommand,
    CreateRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.role.delete import (
    DeleteRoleCommand,
    DeleteRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.role.list_roles import (
    ListRolesInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.role.update import (
    UpdateRoleCommand,
    UpdateRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.update_employee import (
    UpdateEmployeeCommand,
    UpdateEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.presentation.api.v1.schemas import (
    AssignRoleCommandSchema,
    EmployeeListSchema,
    EmployeeRoleSchema,
    EmployeeSchema,
    RoleSchema,
    UpdateEmployeeSchema,
    UpdateRoleSchema,
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


@router.delete(
    "/role-assignments/{assignment_id}", description="Отозвать назначение роли"
)
async def revoke_role(request: Request, assignment_id: UUID) -> JSONResponse:
    command = RevokeRoleCommand(assignment_id=assignment_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(RevokeRoleInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.get("", response_model=EmployeeListSchema, description="Список сотрудников")
async def list_employees(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> EmployeeListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListEmployeesInteractor)
        page = await interactor(
            ListEmployeesQuery(limit=limit, offset=offset, search=search)
        )

    return EmployeeListSchema(
        items=[EmployeeSchema.from_dto(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/roles",
    response_model=list[RoleSchema],
    description="Список ролей",
)
async def list_roles(request: Request) -> list[RoleSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListRolesInteractor)
        items = await interactor()

    return [RoleSchema.from_dto(item) for item in items]


@router.get(
    "/{employee_id}/roles",
    response_model=list[EmployeeRoleSchema],
    description="Роли сотрудника",
)
async def list_employee_roles(
    request: Request, employee_id: UUID
) -> list[EmployeeRoleSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListEmployeeRolesInteractor)
        items = await interactor(ListEmployeeRolesQuery(employee_id=employee_id))

    return [EmployeeRoleSchema.from_dto(item) for item in items]


@router.get(
    "/{employee_id}",
    response_model=EmployeeSchema,
    description="Карточка сотрудника",
)
async def get_employee(request: Request, employee_id: UUID) -> EmployeeSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetEmployeeByIdInteractor)
        employee = await interactor(GetEmployeeByIdQuery(employee_id=employee_id))

    return EmployeeSchema.from_dto(employee)


@router.delete("/roles/{role_id}", description="Удалить роль")
async def delete_role(request: Request, role_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(DeleteRoleInteractor)
        await interactor(DeleteRoleCommand(role_id=role_id))

    return JSONResponse(content={"message": "ok!"})


@router.patch("/{employee_id}", description="Изменить сотрудника")
async def update_employee(
    request: Request, employee_id: UUID, data: UpdateEmployeeSchema
) -> JSONResponse:
    command = UpdateEmployeeCommand(
        employee_id=employee_id,
        provided=frozenset(data.model_fields_set),
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        phone_number=data.phone_number,
        position=data.position,
        is_active=data.is_active,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateEmployeeInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.patch("/roles/{role_id}", description="Изменить роль")
async def update_role(
    request: Request, role_id: UUID, data: UpdateRoleSchema
) -> JSONResponse:
    command = UpdateRoleCommand(
        role_id=role_id,
        provided=frozenset(data.model_fields_set),
        name=data.name,
        description=data.description,
        level=data.level,
        permission_codes=(
            frozenset(data.permission_codes)
            if data.permission_codes is not None
            else None
        ),
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateRoleInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.post(
    "/{employee_id}/password",
    description="Сбросить пароль сотруднику",
)
async def reset_employee_password(request: Request, employee_id: UUID) -> JSONResponse:
    command = ResetEmployeePasswordCommand(employee_id=employee_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ResetEmployeePasswordInteractor)
        issued = await interactor(command)

    return JSONResponse(content=issued)
