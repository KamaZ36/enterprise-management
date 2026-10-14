from uuid import UUID

from fastapi import APIRouter, Request

from myasnaya_derevnya.core.dependencies.container import container
from myasnaya_derevnya.modules.customer.application.interactors.list_customers import (
    GetCustomerInteractor,
    GetCustomerQuery,
    ListCustomersInteractor,
    ListCustomersQuery,
)
from myasnaya_derevnya.modules.customer.presentation.api.v1.schemas import (
    CustomerDetailSchema,
    CustomerListItemSchema,
    CustomerListSchema,
)

router = APIRouter(prefix="/api/customers", tags=["Клиенты"])


@router.get("", response_model=CustomerListSchema, description="Клиенты")
async def list_customers(
    request: Request,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> CustomerListSchema:
    query = ListCustomersQuery(search=search, status=status, limit=limit, offset=offset)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListCustomersInteractor)
        items, total = await interactor(query)

    return CustomerListSchema(
        items=[CustomerListItemSchema.from_dto(item) for item in items], total=total
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerDetailSchema,
    description="Карточка клиента",
)
async def get_customer(request: Request, customer_id: UUID) -> CustomerDetailSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetCustomerInteractor)
        customer = await interactor(GetCustomerQuery(customer_id=customer_id))

    return CustomerDetailSchema.from_dto(customer)
