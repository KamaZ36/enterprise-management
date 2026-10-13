from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.inventory.application.commands import (
    ReceiptLineCommand,
    TransferLineCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.balances.read import (
    GetBalanceInteractor,
    GetBalanceQuery,
    ListBalancesInteractor,
    ListBalancesQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.get import (
    GetReceiptInteractor,
    GetReceiptQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.list import (
    ListReceiptsInteractor,
    ListReceiptsQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.create import (
    CreateTransferCommand,
    CreateTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.get import (
    GetTransferInteractor,
    GetTransferQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.list import (
    ListTransfersInteractor,
    ListTransfersQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.post import (
    PostTransferCommand,
    PostTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.update import (
    UpdateTransferCommand,
    UpdateTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.warehouses.create import (
    CreateWarehouseCommand,
    CreateWarehouseInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.warehouses.list import (
    ListWarehousesInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.warehouses.update import (
    UpdateWarehouseCommand,
    UpdateWarehouseInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    CreateWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.get import (
    GetWriteOffInteractor,
    GetWriteOffQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.list import (
    ListWriteOffsInteractor,
    ListWriteOffsQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
    PostWriteOffCommand,
    PostWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.presentation.api.v1.schemas import (
    BalanceListSchema,
    BalanceSchema,
    CreateReceiptSchema,
    CreateTransferSchema,
    CreateWarehouseSchema,
    CreateWriteOffSchema,
    ReceiptDetailSchema,
    ReceiptLineSchema,
    ReceiptListItemSchema,
    ReceiptListSchema,
    TransferDetailSchema,
    TransferLineSchema,
    TransferListItemSchema,
    TransferListSchema,
    UpdateTransferSchema,
    UpdateWarehouseSchema,
    WarehouseSchema,
    WriteOffDetailSchema,
    WriteOffLineSchema,
    WriteOffListItemSchema,
    WriteOffListSchema,
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

    return [WarehouseSchema.from_dto(warehouse) for warehouse in warehouses]


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
async def list_balances(
    request: Request,
    warehouse_id: UUID,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> BalanceListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListBalancesInteractor)
        items = await interactor(
            ListBalancesQuery(warehouse_id=warehouse_id, search=search)
        )

    return BalanceListSchema(
        items=[BalanceSchema.from_dto(item) for item in items],
        total=len(items),
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
        item = await interactor(query)

    return BalanceSchema.from_dto(item)


@router.get(
    "/receipts",
    response_model=ReceiptListSchema,
    description="Журнал поступлений",
)
async def list_receipts(
    request: Request,
    warehouse_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
) -> ReceiptListSchema:
    query = ListReceiptsQuery(
        warehouse_id=warehouse_id, limit=limit, offset=offset, search=search
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListReceiptsInteractor)
        page = await interactor(query)

    return ReceiptListSchema(
        items=[ReceiptListItemSchema.from_dto(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptDetailSchema,
    description="Карточка поступления",
)
async def get_receipt(request: Request, receipt_id: UUID) -> ReceiptDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetReceiptInteractor)
        detail = await interactor(GetReceiptQuery(receipt_id=receipt_id))

    return ReceiptDetailSchema.from_dto(detail)


@router.get(
    "/write-offs",
    response_model=WriteOffListSchema,
    description="Журнал списаний",
)
async def list_write_offs(
    request: Request,
    warehouse_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
) -> WriteOffListSchema:
    query = ListWriteOffsQuery(
        warehouse_id=warehouse_id, limit=limit, offset=offset, search=search
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListWriteOffsInteractor)
        page = await interactor(query)

    return WriteOffListSchema(
        items=[WriteOffListItemSchema.from_dto(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/write-offs/{write_off_id}",
    response_model=WriteOffDetailSchema,
    description="Карточка списания",
)
async def get_write_off(request: Request, write_off_id: UUID) -> WriteOffDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetWriteOffInteractor)
        detail = await interactor(GetWriteOffQuery(write_off_id=write_off_id))

    return WriteOffDetailSchema.from_dto(detail)


@router.patch(
    "/warehouses/{warehouse_id}",
    description="Изменить склад",
)
async def update_warehouse(
    request: Request, warehouse_id: UUID, data: UpdateWarehouseSchema
) -> JSONResponse:
    command = UpdateWarehouseCommand(
        warehouse_id=warehouse_id,
        name=data.name,
        type_=data.type,
        is_active=data.is_active,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateWarehouseInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


def _transfer_lines(lines: list[TransferLineSchema]) -> list[TransferLineCommand]:
    return [
        TransferLineCommand(
            nomenclature_id=line.nomenclature_id,
            quantity=line.quantity,
            lot_code=line.lot_code,
        )
        for line in lines
    ]


@router.post(
    "/transfers", description="Создать перемещение (черновик)", status_code=201
)
async def create_transfer(request: Request, data: CreateTransferSchema) -> JSONResponse:
    command = CreateTransferCommand(
        from_warehouse_id=data.from_warehouse_id,
        to_warehouse_id=data.to_warehouse_id,
        occurred_at=data.occurred_at,
        lines=_transfer_lines(data.lines),
        comment=data.comment,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateTransferInteractor)
        transfer_id = await interactor(command)

    return JSONResponse(status_code=201, content={"transfer_id": str(transfer_id)})


@router.post("/transfers/{transfer_id}/post", description="Провести перемещение")
async def post_transfer(request: Request, transfer_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(PostTransferInteractor)
        await interactor(PostTransferCommand(transfer_id=transfer_id))

    return JSONResponse(content={"message": "ok"})


@router.get(
    "/transfers",
    response_model=TransferListSchema,
    description="Журнал перемещений",
)
async def list_transfers(
    request: Request,
    warehouse_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
) -> TransferListSchema:
    query = ListTransfersQuery(
        warehouse_id=warehouse_id, limit=limit, offset=offset, search=search
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListTransfersInteractor)
        page = await interactor(query)

    return TransferListSchema(
        items=[TransferListItemSchema.from_dto(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.patch(
    "/transfers/{transfer_id}",
    description="Изменить черновик перемещения",
)
async def update_transfer(
    request: Request, transfer_id: UUID, data: UpdateTransferSchema
) -> JSONResponse:
    command = UpdateTransferCommand(
        transfer_id=transfer_id,
        occurred_at=data.occurred_at,
        lines=_transfer_lines(data.lines),
        comment=data.comment,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateTransferInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok"})


@router.get(
    "/transfers/{transfer_id}",
    response_model=TransferDetailSchema,
    description="Карточка перемещения",
)
async def get_transfer(request: Request, transfer_id: UUID) -> TransferDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetTransferInteractor)
        detail = await interactor(GetTransferQuery(transfer_id=transfer_id))

    return TransferDetailSchema.from_dto(detail)
