from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
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
from myasnaya_derevnya.modules.catalog.application.interactors.list_nomenclatures import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ListNomenclaturesInteractor,
    ListNomenclaturesQuery,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
)
from myasnaya_derevnya.modules.catalog.presentation.api.v1.schemas import (
    CategorySchema,
    CreateCategorySchema,
    CreateNomenclatureSchema,
    CreatePriceListSchema,
    CreatePriceSchema,
    NomenclatureListSchema,
    NomenclatureSchema,
)

router = APIRouter(prefix="/api", tags=["Catalog Module"])


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


@router.post("/price_lists", description="Создать Прайс-Лист")
async def create_price_list(
    request: Request, data: CreatePriceListSchema
) -> JSONResponse:
    command = CreatePriceListCommand(name=data.name)

    async with container(context={Request: request}) as context:
        interactor = await context.get(CreatePriceListInteractor)
        price_list_id = await interactor(command)

    return JSONResponse(status_code=201, content={"price_list_id": str(price_list_id)})


@router.post(
    "/price_lists/{price_list_id}/prices",
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
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
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
