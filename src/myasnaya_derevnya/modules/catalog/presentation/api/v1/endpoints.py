from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.catalog.application.interactors.bind_price_list import (
    BindPriceListCommand,
    BindPriceListInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_category import (
    CreateCategoryCommand,
    CreateCategoryInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_nomenclature import (
    CreateNomenclatureCommand,
    CreateNomenclatureInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_price import (
    CreatePriceCommand,
    CreatePriceInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_price_list import (
    CreatePriceListCommand,
    CreatePriceListInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_categories import (
    ListCategoriesInteractor,
    ListCategoriesQuery,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_nomenclature_prices import (
    ListNomenclaturePricesInteractor,
    ListNomenclaturePricesQuery,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_nomenclatures import (
    ListNomenclaturesInteractor,
    ListNomenclaturesQuery,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_price_lists import (
    ListPriceListPricesInteractor,
    ListPriceListPricesQuery,
    ListPriceListsInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.update_nomenclature import (
    UpdateNomenclatureCommand,
    UpdateNomenclatureInteractor,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.base import (
    PriceListBindingRepository,
)
from myasnaya_derevnya.modules.catalog.presentation.api.v1.schemas import (
    BindPriceListSchema,
    CategorySchema,
    CreateCategorySchema,
    CreateNomenclatureSchema,
    CreatePriceListSchema,
    CreatePriceSchema,
    NomenclatureListSchema,
    NomenclaturePriceListSchema,
    NomenclaturePriceSchema,
    NomenclatureSchema,
    PriceListBindingSchema,
    PriceListEntryListSchema,
    PriceListEntrySchema,
    PriceListPriceListSchema,
    PriceListPriceSchema,
    UpdateCategorySchema,
    UpdateNomenclatureSchema,
)

router = APIRouter(prefix="/api/catalog", tags=["Catalog Module"])


@router.post("/nomenclatures", description="Создать номенклатуру")
async def create_nomenclature(
    request: Request, data: CreateNomenclatureSchema
) -> JSONResponse:
    command = CreateNomenclatureCommand(
        sku=data.sku,
        name=data.name,
        unit=data.unit,
        type_=data.type,
        category_id=data.category_id,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateNomenclatureInteractor)
        nomenclature_id = await interactor(command)

    return JSONResponse(
        status_code=201, content={"nomenclature_id": str(nomenclature_id)}
    )


@router.post("/categories", description="Создать категорию")
async def create_category(request: Request, data: CreateCategorySchema) -> JSONResponse:
    command = CreateCategoryCommand(name=data.name, parent_id=data.parent_id)

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreateCategoryInteractor)
        category_id = await interactor(command)

    return JSONResponse(status_code=201, content={"category_id": str(category_id)})


@router.post("/price-lists", description="Создать Прайс-Лист")
async def create_price_list(
    request: Request, data: CreatePriceListSchema
) -> JSONResponse:
    command = CreatePriceListCommand(name=data.name)

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreatePriceListInteractor)
        price_list_id = await interactor(command)

    return JSONResponse(status_code=201, content={"price_list_id": str(price_list_id)})


@router.post(
    "/price-lists/{price_list_id}/prices",
    description="Создать цену на номенклатуру в конкретном каталоге",
)
async def create_price(
    request: Request, price_list_id: UUID, data: CreatePriceSchema
) -> JSONResponse:
    command = CreatePriceCommand(
        nomenclature_id=data.nomenclature_id,
        price_list_id=price_list_id,
        price=data.price,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreatePriceInteractor)
        price_id = await interactor(command)

    return JSONResponse(status_code=201, content={"price_id": str(price_id)})


@router.get(
    "/nomenclatures",
    response_model=NomenclatureListSchema,
    description="Список номенклатуры",
)
async def list_nomenclatures(
    request: Request,
    search: Annotated[
        str | None, Query(description="Поиск по названию или SKU")
    ] = None,
    type_code: Annotated[NomenclatureType | None, Query(alias="type")] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NomenclatureListSchema:
    query = ListNomenclaturesQuery(
        search=search,
        type_code=type_code.value if type_code else None,
        category_id=category_id,
        limit=limit,
        offset=offset,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListNomenclaturesInteractor)
        page = await interactor(query)

    return NomenclatureListSchema(
        items=[NomenclatureSchema.from_dto(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/categories",
    response_model=list[CategorySchema],
    description="Список категорий",
)
async def list_categories(
    request: Request,
    search: Annotated[str | None, Query(description="Поиск по названию")] = None,
) -> list[CategorySchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListCategoriesInteractor)
        items = await interactor(ListCategoriesQuery(search=search))

    return [CategorySchema.from_dto(item) for item in items]


@router.patch(
    "/nomenclatures/{nomenclature_id}",
    description="Изменить номенклатуру",
)
async def update_nomenclature(
    request: Request, nomenclature_id: UUID, data: UpdateNomenclatureSchema
) -> JSONResponse:
    command = UpdateNomenclatureCommand(
        nomenclature_id=nomenclature_id,
        name=data.name,
        category_id=data.category_id,
        unit=data.unit,
        type_=data.type,
        is_active=data.is_active,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateNomenclatureInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.patch("/categories/{category_id}", description="Переименовать категорию")
async def update_category(
    request: Request, category_id: UUID, data: UpdateCategorySchema
) -> JSONResponse:
    command = UpdateCategoryCommand(category_id=category_id, name=data.name)

    async with container(context={Request: request}) as context:
        interactor = await context.get(UpdateCategoryInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})


@router.put(
    "/org-units/{org_unit_id}/price-list",
    description="Назначить прайс-лист точке",
)
async def bind_price_list(
    request: Request, org_unit_id: UUID, data: BindPriceListSchema
) -> JSONResponse:
    command = BindPriceListCommand(
        org_unit_id=org_unit_id, price_list_id=data.price_list_id
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(BindPriceListInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok"})


@router.get(
    "/org-units/{org_unit_id}/price-list",
    response_model=PriceListBindingSchema | None,
    description="Прайс-лист точки",
)
async def get_price_list_binding(
    request: Request, org_unit_id: UUID
) -> PriceListBindingSchema | None:
    async with container(context={Request: request}) as context:
        repository = await context.get(PriceListBindingRepository)
        binding = await repository.get_by_org_unit(org_unit_id)

    if binding is None:
        return None

    return PriceListBindingSchema(
        org_unit_id=binding.org_unit_id, price_list_id=binding.price_list_id
    )


@router.get(
    "/nomenclatures/{nomenclature_id}/prices",
    response_model=NomenclaturePriceListSchema,
    description="Цены номенклатуры по прайс-листам",
)
async def list_nomenclature_prices(
    request: Request, nomenclature_id: UUID
) -> NomenclaturePriceListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListNomenclaturePricesInteractor)
        items = await interactor(
            ListNomenclaturePricesQuery(nomenclature_id=nomenclature_id)
        )

    return NomenclaturePriceListSchema(
        items=[NomenclaturePriceSchema.from_dto(item) for item in items]
    )


@router.get(
    "/price-lists",
    response_model=PriceListEntryListSchema,
    description="Прайс-листы",
)
async def list_price_lists(request: Request) -> PriceListEntryListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPriceListsInteractor)
        items = await interactor()

    return PriceListEntryListSchema(
        items=[
            PriceListEntrySchema(id=item.id, name=item.name, is_active=item.is_active)
            for item in items
        ]
    )


@router.get(
    "/price-lists/{price_list_id}/prices",
    response_model=PriceListPriceListSchema,
    description="Позиции прайс-листа",
)
async def list_price_list_prices(
    request: Request,
    price_list_id: UUID,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PriceListPriceListSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPriceListPricesInteractor)
        items, total = await interactor(
            ListPriceListPricesQuery(
                price_list_id=price_list_id, search=search, limit=limit, offset=offset
            )
        )

    return PriceListPriceListSchema(
        items=[
            PriceListPriceSchema(
                nomenclature_id=item.nomenclature_id,
                nomenclature_name=item.nomenclature_name,
                sku=item.sku,
                value=item.value,
            )
            for item in items
        ],
        total=total,
    )
