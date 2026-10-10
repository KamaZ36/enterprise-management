from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.inventory.application.commands import (
    ReceiptLineCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_receipt import (
    CreateReceiptCommand,
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_warehouse import (
    CreateWarehouseCommand,
    CreateWarehouseInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_write_off import (
    CreateWriteOffCommand,
    CreateWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.list_warehouses import (
    ListWarehousesInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_receipt import (
    PostReceiptCommand,
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_write_off import (
    PostWriteOffCommand,
    PostWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.read_balances import (
    GetBalanceInteractor,
    GetBalanceQuery,
    ListBalancesInteractor,
    ListBalancesQuery,
)
from myasnaya_derevnya.modules.inventory.presentation.api.v1.schemas import (
    BalanceListSchema,
    BalanceSchema,
    CreateReceiptSchema,
    CreateWarehouseSchema,
    CreateWriteOffSchema,
    ReceiptLineSchema,
    WarehouseSchema,
    WriteOffLineSchema,
)

router = APIRouter(prefix="/api/inventory", tags=["Склад"])


def _receipt_lines(lines: list[ReceiptLineSchema]) -> list[ReceiptLineCommand]:
    return [
        ReceiptLineCommand(
            nomenclature_id=line.nomenclature_id,
            quantity=line.quantity,
            unit_cost=line.unit_cost,
            lot_code=line.lot_code,
            expires_at=line.expires_at,
        )
        for line in lines
    ]


def _write_off_lines(lines: list[WriteOffLineSchema]) -> list[WriteOffLineCommand]:
    return [
        WriteOffLineCommand(
            nomenclature_id=line.nomenclature_id,
            quantity=line.quantity,
            lot_code=line.lot_code,
        )
        for line in lines
    ]


@router.post("/warehouses", description="Создать склад", status_code=201)
async def create_warehouse(
    request: Request, data: CreateWarehouseSchema
) -> JSONResponse:
    command = CreateWarehouseCommand(
        org_unit_id=data.org_unit_id,
        code=data.code,
        name=data.name,
        type=data.type,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateWarehouseInteractor)
        warehouse_id = await interactor(command)

    return JSONResponse(status_code=201, content={"warehouse_id": str(warehouse_id)})


@router.get(
    "/warehouses", response_model=list[WarehouseSchema], description="Список складов"
)
async def list_warehouses(request: Request) -> list[WarehouseSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListWarehousesInteractor)
        warehouses = await interactor()

    return [WarehouseSchema.from_entity(warehouse) for warehouse in warehouses]


@router.post("/receipts", description="Создать поступление (черновик)", status_code=201)
async def create_receipt(request: Request, data: CreateReceiptSchema) -> JSONResponse:
    command = CreateReceiptCommand(
        warehouse_id=data.warehouse_id,
        occurred_at=data.occurred_at,
        lines=_receipt_lines(data.lines),
        supplier_name=data.supplier_name,
        supplier_document_number=data.supplier_document_number,
        comment=data.comment,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateReceiptInteractor)
        receipt_id = await interactor(command)

    return JSONResponse(status_code=201, content={"receipt_id": str(receipt_id)})


@router.post("/receipts/{receipt_id}/post", description="Провести поступление")
async def post_receipt(request: Request, receipt_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(PostReceiptInteractor)
        await interactor(PostReceiptCommand(receipt_id=receipt_id))

    return JSONResponse(content={"message": "ok"})


@router.post("/write-offs", description="Создать списание (черновик)", status_code=201)
async def create_write_off(
    request: Request, data: CreateWriteOffSchema
) -> JSONResponse:
    command = CreateWriteOffCommand(
        warehouse_id=data.warehouse_id,
        occurred_at=data.occurred_at,
        lines=_write_off_lines(data.lines),
        reason=data.reason,
        comment=data.comment,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateWriteOffInteractor)
        write_off_id = await interactor(command)

    return JSONResponse(status_code=201, content={"write_off_id": str(write_off_id)})


@router.post("/write-offs/{write_off_id}/post", description="Провести списание")
async def post_write_off(request: Request, write_off_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(PostWriteOffInteractor)
        await interactor(PostWriteOffCommand(write_off_id=write_off_id))

    return JSONResponse(content={"message": "ok"})


@router.get(
    "/warehouses/{warehouse_id}/balances",
    response_model=BalanceListSchema,
    description="Остатки склада",
)
async def list_balances(request: Request, warehouse_id: UUID) -> BalanceListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListBalancesInteractor)
        views = await interactor(ListBalancesQuery(warehouse_id=warehouse_id))

    return BalanceListSchema(
        items=[BalanceSchema.from_view(view) for view in views],
        total=len(views),
    )


@router.get(
    "/warehouses/{warehouse_id}/balances/{nomenclature_id}",
    response_model=BalanceSchema,
    description="Остаток и себестоимость по номенклатуре",
)
async def get_balance(
    request: Request, warehouse_id: UUID, nomenclature_id: UUID
) -> BalanceSchema:
    query = GetBalanceQuery(warehouse_id=warehouse_id, nomenclature_id=nomenclature_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(GetBalanceInteractor)
        view = await interactor(query)

    return BalanceSchema.from_view(view)
