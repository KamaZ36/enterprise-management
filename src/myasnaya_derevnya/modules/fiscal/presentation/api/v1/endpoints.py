from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.fiscal.application.interactors.bind_cash_register import (
    BindCashRegisterCommand,
    BindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.create_cash_register import (
    CreateCashRegisterCommand,
    CreateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.get_cash_register import (
    GetCashRegisterInteractor,
    GetCashRegisterQuery,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_cash_registers import (
    ListCashRegistersInteractor,
    ListCashRegistersQuery,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_stock_locations import (
    ListStockLocationsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.unbind_cash_register import (
    UnbindCashRegisterCommand,
    UnbindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.update_cash_register import (
    UpdateCashRegisterCommand,
    UpdateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.presentation.api.v1.schemas import (
    BindCashRegisterSchema,
    CashRegisterDetailSchema,
    CashRegisterSchema,
    CreateCashRegisterSchema,
    StockLocationOptionSchema,
    UnbindCashRegisterSchema,
    UpdateCashRegisterSchema,
)

router = APIRouter(prefix="/api/fiscal", tags=["Кассы"])


@router.post("/cash-registers", description="Добавить кассу")
async def create_cash_register(
    request: Request, data: CreateCashRegisterSchema
) -> JSONResponse:
    command = CreateCashRegisterCommand(**data.model_dump())

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateCashRegisterInteractor)
        cash_register_id = await interactor(command)

    return JSONResponse(
        status_code=201, content={"cash_register_id": str(cash_register_id)}
    )


@router.get(
    "/stock-locations",
    response_model=list[StockLocationOptionSchema],
    description="Точки, к которым можно привязать кассу",
)
async def list_stock_locations(
    request: Request,
) -> list[StockLocationOptionSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListStockLocationsInteractor)
        items = await interactor()

    return [StockLocationOptionSchema.from_dto(item) for item in items]


@router.get(
    "/cash-registers",
    response_model=list[CashRegisterSchema],
    description="Список касс",
)
async def list_cash_registers(
    request: Request,
    org_unit_id: Annotated[UUID | None, Query()] = None,
    at: Annotated[datetime | None, Query()] = None,
) -> list[CashRegisterSchema]:
    query = ListCashRegistersQuery(org_unit_id=org_unit_id, at=at)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListCashRegistersInteractor)
        items = await interactor(query)

    return [CashRegisterSchema.from_dto(item) for item in items]


@router.get(
    "/cash-registers/{cash_register_id}",
    response_model=CashRegisterDetailSchema,
    description="Касса с историей привязок",
)
async def get_cash_register(
    request: Request, cash_register_id: UUID
) -> CashRegisterDetailSchema:
    query = GetCashRegisterQuery(cash_register_id=cash_register_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(GetCashRegisterInteractor)
        item = await interactor(query)

    return CashRegisterDetailSchema.from_detail(item)


@router.patch("/cash-registers/{cash_register_id}", description="Изменить кассу")
async def update_cash_register(
    request: Request, cash_register_id: UUID, data: UpdateCashRegisterSchema
) -> JSONResponse:
    command = UpdateCashRegisterCommand(
        cash_register_id=cash_register_id,
        provided=frozenset(data.model_fields_set),
        **data.model_dump(),
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateCashRegisterInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.post(
    "/cash-registers/{cash_register_id}/bind",
    description="Привязать кассу к подразделению",
)
async def bind_cash_register(
    request: Request, cash_register_id: UUID, data: BindCashRegisterSchema
) -> JSONResponse:
    command = BindCashRegisterCommand(
        cash_register_id=cash_register_id,
        org_unit_id=data.org_unit_id,
        effective_from=data.effective_from,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(BindCashRegisterInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.post(
    "/cash-registers/{cash_register_id}/unbind",
    description="Закрыть привязку кассы",
)
async def unbind_cash_register(
    request: Request, cash_register_id: UUID, data: UnbindCashRegisterSchema
) -> JSONResponse:
    command = UnbindCashRegisterCommand(
        cash_register_id=cash_register_id,
        effective_to=data.effective_to,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UnbindCashRegisterInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})
