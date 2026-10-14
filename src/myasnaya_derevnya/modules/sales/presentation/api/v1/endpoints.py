from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies.container import container
from myasnaya_derevnya.modules.sales.application.interactors.cancel_order import (
    CancelOrderCommand,
    CancelOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.confirm_order import (
    ConfirmOrderCommand,
    ConfirmOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.create_order import (
    CreateOrderCommand,
    CreateOrderInteractor,
    OrderLineCommand,
)
from myasnaya_derevnya.modules.sales.application.interactors.get_my_order import (
    GetMyOrderInteractor,
    GetMyOrderQuery,
)
from myasnaya_derevnya.modules.sales.application.interactors.get_order import (
    GetOrderInteractor,
    GetOrderQuery,
)
from myasnaya_derevnya.modules.sales.application.interactors.list_my_orders import (
    ListMyOrdersInteractor,
    ListMyOrdersQuery,
)
from myasnaya_derevnya.modules.sales.application.interactors.list_orders import (
    ListOrdersInteractor,
    ListOrdersQuery,
)
from myasnaya_derevnya.modules.sales.presentation.api.v1.schemas import (
    CreatedOrderSchema,
    CreateOrderSchema,
    MyOrderDetailSchema,
    MyOrderListItemSchema,
    MyOrderListSchema,
    OrderDetailSchema,
    OrderListItemSchema,
    OrderListSchema,
)

router = APIRouter(prefix="/api/sales", tags=["Заказы"])


@router.get("/orders", response_model=OrderListSchema, description="Заказы")
async def list_orders(
    request: Request,
    org_unit_id: UUID | None = None,
    customer_id: UUID | None = None,
    statuses: str | None = None,
    day: date | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> OrderListSchema:
    query = ListOrdersQuery(
        org_unit_id=org_unit_id,
        customer_id=customer_id,
        statuses=statuses.split(",") if statuses else None,
        day=day,
        search=search,
        limit=limit,
        offset=offset,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListOrdersInteractor)
        items, total = await interactor(query)

    return OrderListSchema(
        items=[OrderListItemSchema.from_dto(item) for item in items], total=total
    )


@router.post("/orders", response_model=CreatedOrderSchema, description="Создать заказ")
async def create_order(request: Request, data: CreateOrderSchema) -> JSONResponse:
    command = CreateOrderCommand(
        org_unit_id=data.org_unit_id,
        channel=data.channel,
        customer_id=data.customer_id,
        planned_at=data.planned_at,
        comment=data.comment,
        lines=tuple(
            OrderLineCommand(
                nomenclature_id=line.nomenclature_id, quantity=line.quantity
            )
            for line in data.lines
        ),
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateOrderInteractor)
        order_id = await interactor(command)

    return JSONResponse(status_code=201, content={"order_id": str(order_id)})


@router.get(
    "/orders/{order_id}",
    response_model=OrderDetailSchema,
    description="Карточка заказа",
)
async def get_order(request: Request, order_id: UUID) -> OrderDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetOrderInteractor)
        order = await interactor(GetOrderQuery(order_id=order_id))

    return OrderDetailSchema.from_dto(order)


@router.post("/orders/{order_id}/confirm", description="Подтвердить заказ")
async def confirm_order(request: Request, order_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ConfirmOrderInteractor)
        await interactor(ConfirmOrderCommand(order_id=order_id))

    return JSONResponse(content={"message": "ok"})


@router.post("/orders/{order_id}/cancel", description="Отменить заказ")
async def cancel_order(request: Request, order_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CancelOrderInteractor)
        await interactor(CancelOrderCommand(order_id=order_id))

    return JSONResponse(content={"message": "ok"})


@router.get("/me/orders", response_model=OrderListSchema, description="Мои заказы")
async def list_my_orders(
    request: Request,
    statuses: str | None = None,
    day: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> MyOrderListSchema:
    query = ListMyOrdersQuery(
        statuses=statuses.split(",") if statuses else None,
        day=day,
        limit=limit,
        offset=offset,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListMyOrdersInteractor)
        items, total = await interactor(query)

    return MyOrderListSchema(
        items=[MyOrderListItemSchema.from_dto(item) for item in items], total=total
    )


@router.get(
    "/me/orders/{order_id}",
    response_model=MyOrderDetailSchema,
    description="Моя карточка заказа",
)
async def get_my_order(request: Request, order_id: UUID) -> MyOrderDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetMyOrderInteractor)
        order = await interactor(GetMyOrderQuery(order_id=order_id))

    return MyOrderDetailSchema.from_dto(order)


@router.post(
    "/me/orders", response_model=CreatedOrderSchema, description="Оформить заказ"
)
async def create_my_order(request: Request, data: CreateOrderSchema) -> JSONResponse:
    command = CreateOrderCommand(
        org_unit_id=data.org_unit_id,
        channel=OrderChannel.SITE,
        planned_at=data.planned_at,
        comment=data.comment,
        lines=tuple(
            OrderLineCommand(
                nomenclature_id=line.nomenclature_id, quantity=line.quantity
            )
            for line in data.lines
        ),
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateOrderInteractor)
        order_id = await interactor(command)

    return JSONResponse(status_code=201, content={"order_id": str(order_id)})


@router.post("/me/orders/{order_id}/cancel", description="Отменить свой заказ")
async def cancel_my_order(request: Request, order_id: UUID) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(CancelOrderInteractor)
        await interactor(CancelOrderCommand(order_id=order_id))

    return JSONResponse(content={"message": "ok"})
