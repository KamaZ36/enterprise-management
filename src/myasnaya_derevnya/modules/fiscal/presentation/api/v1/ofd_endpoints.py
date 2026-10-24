from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.fiscal.application.interactors.get_ofd_receipt import (
    GetOfdReceiptInteractor,
    GetOfdReceiptQuery,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_ofd_receipts import (
    ListOfdReceiptsInteractor,
    ListOfdReceiptsQuery,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.map_ofd_receipt_line import (
    MapOfdReceiptLineCommand,
    MapOfdReceiptLineInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ofd_receipt import (
    PostOfdReceiptCommand,
    PostOfdReceiptInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ready_ofd_receipts import (
    PostReadyOfdReceiptsCommand,
    PostReadyOfdReceiptsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.sync_ofd_receipts import (
    SyncOfdReceiptsCommand,
    SyncOfdReceiptsInteractor,
)
from myasnaya_derevnya.modules.fiscal.presentation.api.v1.ofd_schemas import (
    MapOfdReceiptLineResultSchema,
    MapOfdReceiptLineSchema,
    OfdBatchPostResultSchema,
    OfdPostResultSchema,
    OfdReceiptDetailSchema,
    OfdReceiptListSchema,
    PostReadyOfdReceiptsSchema,
    SyncOfdReceiptsResultSchema,
    SyncOfdReceiptsSchema,
)

router = APIRouter(prefix="/ofd", tags=["Чеки ОФД"])


@router.post(
    "/receipts/sync",
    response_model=SyncOfdReceiptsResultSchema,
    description="Загрузить чеки из ОФД за период",
)
async def sync_receipts(
    request: Request, data: SyncOfdReceiptsSchema
) -> SyncOfdReceiptsResultSchema:
    command = SyncOfdReceiptsCommand(
        reg_number=data.reg_number,
        date_from=data.date_from,
        date_to=data.date_to,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(SyncOfdReceiptsInteractor)
        result = await interactor(command)

    return SyncOfdReceiptsResultSchema.from_dto(result)


@router.get(
    "/receipts",
    response_model=OfdReceiptListSchema,
    description="Список сохранённых чеков ОФД",
)
async def list_receipts(
    request: Request,
    status: Annotated[str | None, Query(max_length=24)] = None,
    reg_number: Annotated[str | None, Query(max_length=32)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OfdReceiptListSchema:
    query = ListOfdReceiptsQuery(
        status=status,
        reg_number=reg_number,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListOfdReceiptsInteractor)
        page = await interactor(query)

    return OfdReceiptListSchema.from_dto(page)


@router.post(
    "/receipts/post-ready",
    response_model=OfdBatchPostResultSchema,
    description="Провести все готовые чеки ОФД",
)
async def post_ready_receipts(
    request: Request, data: PostReadyOfdReceiptsSchema
) -> OfdBatchPostResultSchema:
    command = PostReadyOfdReceiptsCommand(limit=data.limit)

    async with container(context={Request: request}) as context:
        interactor = await context.get(PostReadyOfdReceiptsInteractor)
        result = await interactor(command)

    return OfdBatchPostResultSchema.from_dto(result)


@router.get(
    "/receipts/{receipt_id}",
    response_model=OfdReceiptDetailSchema,
    description="Чек ОФД с товарными строками",
)
async def get_receipt(
    request: Request, receipt_id: UUID
) -> OfdReceiptDetailSchema:
    query = GetOfdReceiptQuery(receipt_id=receipt_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(GetOfdReceiptInteractor)
        result = await interactor(query)

    return OfdReceiptDetailSchema.from_dto(result)


@router.post(
    "/receipts/{receipt_id}/post",
    response_model=OfdPostResultSchema,
    description="Провести чек ОФД по складу",
)
async def post_receipt(
    request: Request, receipt_id: UUID
) -> OfdPostResultSchema:
    command = PostOfdReceiptCommand(receipt_id=receipt_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(PostOfdReceiptInteractor)
        result = await interactor(command)

    return OfdPostResultSchema.from_dto(result)


@router.post(
    "/lines/{line_id}/map",
    response_model=MapOfdReceiptLineResultSchema,
    description="Сопоставить строку чека с номенклатурой",
)
async def map_line(
    request: Request, line_id: UUID, data: MapOfdReceiptLineSchema
) -> MapOfdReceiptLineResultSchema:
    command = MapOfdReceiptLineCommand(
        line_id=line_id,
        nomenclature_id=data.nomenclature_id,
        remember_barcode=data.remember_barcode,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(MapOfdReceiptLineInteractor)
        result = await interactor(command)

    return MapOfdReceiptLineResultSchema.from_dto(result)
