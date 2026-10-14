from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.production.application.interactors.cancel_production_order import (
    CancelProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.create_production_order import (
    CreateProductionOrderCommand,
    CreateProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.create_tech_card import (
    CreateTechCardCommand,
    CreateTechCardInteractor,
    TechCardLineCommand,
)
from myasnaya_derevnya.modules.production.application.interactors.get_production_order import (
    GetProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.get_tech_card import (
    GetTechCardInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.list_production_orders import (
    ListProductionOrdersInteractor,
    ListProductionOrdersQuery,
)
from myasnaya_derevnya.modules.production.application.interactors.list_tech_cards import (
    ListTechCardsInteractor,
    ListTechCardsQuery,
)
from myasnaya_derevnya.modules.production.application.interactors.post_production_order import (
    PostProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.update_production_order import (
    ProductionOrderActualCommand,
    UpdateProductionOrderCommand,
    UpdateProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.presentation.api.v1.schemas import (
    CreatedProductionSchema,
    CreateProductionOrderSchema,
    CreateTechCardSchema,
    ProductionOrderDetailSchema,
    ProductionOrderListItemSchema,
    ProductionOrderListSchema,
    TechCardDetailSchema,
    TechCardListItemSchema,
    TechCardListSchema,
    UpdateProductionOrderSchema,
)

router = APIRouter(prefix="/api/production", tags=["Производство"])


@router.get(
    "/tech-cards",
    response_model=TechCardListSchema,
    description="Техкарты: все редакции",
)
async def list_tech_cards(
    request: Request,
    search: Annotated[
        str | None, Query(description="Поиск по коду или названию")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TechCardListSchema:
    query = ListTechCardsQuery(search=search, limit=limit, offset=offset)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListTechCardsInteractor)
        page = await interactor(query)

    return TechCardListSchema(
        items=[TechCardListItemSchema.from_dto(item) for item in page.items],
        total=page.total,
    )


@router.post(
    "/tech-cards",
    response_model=CreatedProductionSchema,
    description="Создать техкарту или новую редакцию",
)
async def create_tech_card(
    request: Request, data: CreateTechCardSchema
) -> JSONResponse:
    command = CreateTechCardCommand(
        code=data.code,
        name=data.name,
        basis=data.basis,
        valid_from=data.valid_from,
        comment=data.comment,
        lines=tuple(
            TechCardLineCommand(
                role=line.role,
                quantity=line.quantity,
                nomenclature_id=line.nomenclature_id,
                loss_kind=line.loss_kind,
                output_kind=line.output_kind,
                cost_coefficient=line.cost_coefficient,
            )
            for line in data.lines
        ),
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateTechCardInteractor)
        tech_card_id = await interactor(command)

    return JSONResponse(status_code=201, content={"id": str(tech_card_id)})


@router.get(
    "/tech-cards/{tech_card_id}",
    response_model=TechCardDetailSchema,
    description="Техкарта: состав и нормы",
)
async def get_tech_card(
    request: Request, tech_card_id: UUID
) -> TechCardDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetTechCardInteractor)
        tech_card = await interactor(tech_card_id)

    return TechCardDetailSchema.from_dto(tech_card)


@router.get(
    "/orders",
    response_model=ProductionOrderListSchema,
    description="Производственные задания",
)
async def list_production_orders(
    request: Request,
    warehouse_id: Annotated[UUID | None, Query()] = None,
    statuses: Annotated[
        str | None, Query(description="Статусы через запятую")
    ] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductionOrderListSchema:
    query = ListProductionOrdersQuery(
        warehouse_id=warehouse_id,
        statuses=tuple(statuses.split(",")) if statuses else None,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
        offset=offset,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListProductionOrdersInteractor)
        page = await interactor(query)

    return ProductionOrderListSchema(
        items=[
            ProductionOrderListItemSchema.from_dto(item) for item in page.items
        ],
        total=page.total,
    )


@router.post(
    "/orders",
    response_model=CreatedProductionSchema,
    description="Создать производственное задание",
)
async def create_production_order(
    request: Request, data: CreateProductionOrderSchema
) -> JSONResponse:
    command = CreateProductionOrderCommand(
        warehouse_id=data.warehouse_id,
        tech_card_id=data.tech_card_id,
        batch_count=data.batch_count,
        occurred_at=data.occurred_at,
        comment=data.comment,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateProductionOrderInteractor)
        order_id = await interactor(command)

    return JSONResponse(status_code=201, content={"id": str(order_id)})


@router.get(
    "/orders/{order_id}",
    response_model=ProductionOrderDetailSchema,
    description="Производственное задание: входы, выходы и потери",
)
async def get_production_order(
    request: Request, order_id: UUID
) -> ProductionOrderDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetProductionOrderInteractor)
        order = await interactor(order_id)

    return ProductionOrderDetailSchema.from_dto(order)


@router.patch(
    "/orders/{order_id}",
    description="Ввести факт по строкам черновика",
)
async def update_production_order(
    request: Request, order_id: UUID, data: UpdateProductionOrderSchema
) -> JSONResponse:
    command = UpdateProductionOrderCommand(
        order_id=order_id,
        actuals=tuple(
            ProductionOrderActualCommand(
                line_id=actual.line_id, quantity=actual.quantity
            )
            for actual in data.actuals
        ),
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateProductionOrderInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok"})


@router.post("/orders/{order_id}/post", description="Провести задание")
async def post_production_order(request: Request, order_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(PostProductionOrderInteractor)
        await interactor(order_id)

    return JSONResponse(content={"message": "ok"})


@router.post("/orders/{order_id}/cancel", description="Отменить черновик задания")
async def cancel_production_order(request: Request, order_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CancelProductionOrderInteractor)
        await interactor(order_id)

    return JSONResponse(content={"message": "ok"})
