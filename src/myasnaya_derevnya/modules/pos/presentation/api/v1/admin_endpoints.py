from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.pos.application.interactors.create_source import (
    CreatePosSourceCommand,
    CreatePosSourceInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.delete_product_mapping import (
    DeletePosProductMappingCommand,
    DeletePosProductMappingInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.get_receipt import (
    GetPosReceiptInteractor,
    GetPosReceiptQuery,
)
from myasnaya_derevnya.modules.pos.application.interactors.issue_agent_key import (
    IssuePosAgentKeyCommand,
    IssuePosAgentKeyInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_agents import (
    ListPosAgentsInteractor,
    ListPosAgentsQuery,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_locations import (
    ListPosLocationsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_product_mappings import (
    ListPosProductMappingsInteractor,
    ListPosProductMappingsQuery,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_receipts import (
    ListPosReceiptsInteractor,
    ListPosReceiptsQuery,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_sources import (
    ListPosSourcesInteractor,
    ListPosSourcesQuery,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_unmapped_products import (
    ListPosUnmappedProductsInteractor,
    ListPosUnmappedProductsQuery,
)
from myasnaya_derevnya.modules.pos.application.interactors.post_pending_receipts import (
    PostPendingPosReceiptsCommand,
    PostPendingPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.post_receipt import (
    PostPosReceiptCommand,
    PostPosReceiptInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.rotate_agent_key import (
    RotatePosAgentKeyCommand,
    RotatePosAgentKeyInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.set_agent_active import (
    SetPosAgentActiveCommand,
    SetPosAgentActiveInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.update_source import (
    UpdatePosSourceCommand,
    UpdatePosSourceInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.upsert_product_mapping import (
    UpsertPosProductMappingCommand,
    UpsertPosProductMappingInteractor,
)
from myasnaya_derevnya.modules.pos.presentation.api.v1.schemas import (
    CreatePosSourceSchema,
    IssuePosAgentKeySchema,
    PosAgentKeySchema,
    PosAgentSchema,
    PosBatchPostResultSchema,
    PosLocationSchema,
    PosPostResultSchema,
    PosProductMappingSchema,
    PosReceiptDetailSchema,
    PosReceiptListSchema,
    PosSourceSchema,
    PostPendingPosReceiptsSchema,
    PosUnmappedProductSchema,
    SetPosAgentActiveSchema,
    UpdatePosSourceSchema,
    UpsertPosProductMappingSchema,
)

router = APIRouter(prefix="/api/pos", tags=["Продажи DoKa"])


@router.get(
    "/sources",
    response_model=list[PosSourceSchema],
    description="Источники продаж DoKa",
)
async def list_sources(request: Request) -> list[PosSourceSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPosSourcesInteractor)
        items = await interactor(ListPosSourcesQuery())

    return [PosSourceSchema.from_dto(item) for item in items]


@router.get(
    "/locations",
    response_model=list[PosLocationSchema],
    description="Складские локации для привязки кассы DoKa",
)
async def list_locations(request: Request) -> list[PosLocationSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPosLocationsInteractor)
        items = await interactor()

    return [PosLocationSchema.from_dto(item) for item in items]


@router.post(
    "/sources",
    response_model=PosSourceSchema,
    description="Зарегистрировать кассу DoKa",
)
async def create_source(
    request: Request, data: CreatePosSourceSchema
) -> PosSourceSchema:
    command = CreatePosSourceCommand(
        doka_org_id=data.doka_org_id,
        name=data.name,
        org_unit_id=data.org_unit_id,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreatePosSourceInteractor)
        item = await interactor(command)

    return PosSourceSchema.from_dto(item)


@router.patch(
    "/sources/{source_id}",
    response_model=PosSourceSchema,
    description="Изменить источник DoKa",
)
async def update_source(
    request: Request, source_id: UUID, data: UpdatePosSourceSchema
) -> PosSourceSchema:
    command = UpdatePosSourceCommand(
        source_id=source_id,
        name=data.name,
        org_unit_id=data.org_unit_id,
        is_active=data.is_active,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdatePosSourceInteractor)
        item = await interactor(command)

    return PosSourceSchema.from_dto(item)


@router.get(
    "/sources/{source_id}/agents",
    response_model=list[PosAgentSchema],
    description="Агенты источника DoKa",
)
async def list_agents(
    request: Request, source_id: UUID
) -> list[PosAgentSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPosAgentsInteractor)
        items = await interactor(ListPosAgentsQuery(source_id=source_id))

    return [PosAgentSchema.from_dto(item) for item in items]


@router.post(
    "/sources/{source_id}/agents/keys",
    response_model=PosAgentKeySchema,
    description="Выдать ключ агенту кассы",
)
async def issue_agent_key(
    request: Request, source_id: UUID, data: IssuePosAgentKeySchema
) -> PosAgentKeySchema:
    command = IssuePosAgentKeyCommand(
        source_id=source_id,
        install_id=data.install_id,
        hostname=data.hostname,
        version=data.version,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(IssuePosAgentKeyInteractor)
        result = await interactor(command)

    return PosAgentKeySchema(
        agent=PosAgentSchema.from_dto(result.agent),
        api_key=result.api_key,
    )


@router.post(
    "/agents/{agent_id}/keys/rotate",
    response_model=PosAgentKeySchema,
    description="Перевыпустить ключ агента",
)
async def rotate_agent_key(
    request: Request, agent_id: UUID
) -> PosAgentKeySchema:
    command = RotatePosAgentKeyCommand(agent_id=agent_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(RotatePosAgentKeyInteractor)
        result = await interactor(command)

    return PosAgentKeySchema(
        agent=PosAgentSchema.from_dto(result.agent),
        api_key=result.api_key,
    )


@router.patch(
    "/agents/{agent_id}/active",
    response_model=PosAgentSchema,
    description="Включить или отключить агента",
)
async def set_agent_active(
    request: Request, agent_id: UUID, data: SetPosAgentActiveSchema
) -> PosAgentSchema:
    command = SetPosAgentActiveCommand(
        agent_id=agent_id, is_active=data.is_active
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(SetPosAgentActiveInteractor)
        item = await interactor(command)

    return PosAgentSchema.from_dto(item)


@router.get(
    "/receipts",
    response_model=PosReceiptListSchema,
    description="Чеки DoKa",
)
async def list_receipts(
    request: Request,
    source_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query(max_length=24)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    org_unit_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PosReceiptListSchema:
    query = ListPosReceiptsQuery(
        source_id=source_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        org_unit_id=org_unit_id,
        limit=limit,
        offset=offset,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPosReceiptsInteractor)
        page = await interactor(query)

    return PosReceiptListSchema.from_dto(page)


@router.post(
    "/receipts/post-pending",
    response_model=PosBatchPostResultSchema,
    description="Провести все непринятые складом чеки DoKa",
)
async def post_pending_receipts(
    request: Request, data: PostPendingPosReceiptsSchema
) -> PosBatchPostResultSchema:
    command = PostPendingPosReceiptsCommand(limit=data.limit)

    async with container(context={Request: request}) as context:
        interactor = await context.get(PostPendingPosReceiptsInteractor)
        result = await interactor(command)

    return PosBatchPostResultSchema.from_dto(result)


@router.get(
    "/receipts/{receipt_id}",
    response_model=PosReceiptDetailSchema,
    description="Чек DoKa с товарными строками",
)
async def get_receipt(
    request: Request, receipt_id: UUID
) -> PosReceiptDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetPosReceiptInteractor)
        item = await interactor(GetPosReceiptQuery(receipt_id=receipt_id))

    return PosReceiptDetailSchema.from_dto(item)


@router.post(
    "/receipts/{receipt_id}/post",
    response_model=PosPostResultSchema,
    description="Провести чек DoKa по складу",
)
async def post_receipt(
    request: Request, receipt_id: UUID
) -> PosPostResultSchema:
    command = PostPosReceiptCommand(receipt_id=receipt_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(PostPosReceiptInteractor)
        result = await interactor(command)

    return PosPostResultSchema.from_dto(result)


@router.get(
    "/sources/{source_id}/product-map",
    response_model=list[PosProductMappingSchema],
    description="Сопоставления товаров DoKa",
)
async def list_product_mappings(
    request: Request,
    source_id: UUID,
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> list[PosProductMappingSchema]:
    query = ListPosProductMappingsQuery(source_id=source_id, search=search)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPosProductMappingsInteractor)
        items = await interactor(query)

    return [PosProductMappingSchema.from_dto(item) for item in items]


@router.get(
    "/sources/{source_id}/unmapped-products",
    response_model=list[PosUnmappedProductSchema],
    description="Товары DoKa из чеков, ещё не сопоставленные с номенклатурой",
)
async def list_unmapped_products(
    request: Request,
    source_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[PosUnmappedProductSchema]:
    query = ListPosUnmappedProductsQuery(source_id=source_id, limit=limit)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPosUnmappedProductsInteractor)
        items = await interactor(query)

    return [PosUnmappedProductSchema.from_dto(item) for item in items]


@router.put(
    "/sources/{source_id}/product-map",
    response_model=PosProductMappingSchema,
    description="Сопоставить товар DoKa с номенклатурой",
)
async def upsert_product_mapping(
    request: Request, source_id: UUID, data: UpsertPosProductMappingSchema
) -> PosProductMappingSchema:
    command = UpsertPosProductMappingCommand(
        source_id=source_id,
        doka_product_guid=data.doka_product_guid,
        nomenclature_id=data.nomenclature_id,
        unit_factor=data.unit_factor,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpsertPosProductMappingInteractor)
        item = await interactor(command)

    return PosProductMappingSchema.from_dto(item)


@router.delete(
    "/product-map/{mapping_id}",
    status_code=204,
    description="Удалить сопоставление товара DoKa",
)
async def delete_product_mapping(
    request: Request, mapping_id: UUID
) -> None:
    command = DeletePosProductMappingCommand(mapping_id=mapping_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(DeletePosProductMappingInteractor)
        await interactor(command)
