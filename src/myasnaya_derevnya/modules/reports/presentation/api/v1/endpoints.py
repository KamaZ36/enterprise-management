from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.core.timezone import company_today
from myasnaya_derevnya.modules.reports.application.errors import (
    InvalidReportPeriodError,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_stock import (
    GetStockReportInteractor,
    StockReportQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_summary import (
    GetSummaryInteractor,
    SummaryQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_production import (
    ListProductionReportInteractor,
    ProductionReportQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_sales import (
    ListSalesReportInteractor,
    SalesReportQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_write_offs import (
    ListWriteOffReportInteractor,
    WriteOffReportQuery,
)
from myasnaya_derevnya.modules.reports.presentation.api.v1.schemas import (
    ProductionReportRowSchema,
    ProductionReportSchema,
    ReportSummarySchema,
    SalesReportSchema,
    StockReportRowSchema,
    StockReportSchema,
    WriteOffReportRowSchema,
    WriteOffReportSchema,
)

router = APIRouter(prefix="/api/reports", tags=["Отчёты"])

DEFAULT_PERIOD_DAYS = 7


def _period(
    date_from: date | None, date_to: date | None
) -> tuple[date, date]:
    today = company_today()
    start = date_from or today - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
    end = date_to or today

    if end < start:
        raise InvalidReportPeriodError()

    return start, end


@router.get(
    "/summary",
    response_model=ReportSummarySchema,
    description="Сводка: продажи, склад, производство и списания",
)
async def get_summary(
    request: Request,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    org_unit_id: Annotated[UUID | None, Query()] = None,
) -> ReportSummarySchema:
    start, end = _period(date_from, date_to)

    async with container(context={Request: request}) as context:
        interactor = await context.get(GetSummaryInteractor)
        summary = await interactor(
            SummaryQuery(date_from=start, date_to=end, org_unit_id=org_unit_id)
        )

    return ReportSummarySchema.from_dto(summary)


@router.get(
    "/sales",
    response_model=SalesReportSchema,
    description="Продажи по кассам: выручка, себестоимость и маржа",
)
async def list_sales(
    request: Request,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    org_unit_id: Annotated[UUID | None, Query()] = None,
) -> SalesReportSchema:
    start, end = _period(date_from, date_to)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListSalesReportInteractor)
        report = await interactor(
            SalesReportQuery(
                date_from=start, date_to=end, org_unit_id=org_unit_id
            )
        )

    return SalesReportSchema.from_dto(report)


@router.get(
    "/stock",
    response_model=StockReportSchema,
    description="Остатки и стоимость склада по точкам",
)
async def get_stock(
    request: Request,
    org_unit_id: Annotated[UUID | None, Query()] = None,
) -> StockReportSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetStockReportInteractor)
        items = await interactor(StockReportQuery(org_unit_id=org_unit_id))

    return StockReportSchema(
        items=[StockReportRowSchema.from_dto(item) for item in items]
    )


@router.get(
    "/production",
    response_model=ProductionReportSchema,
    description="Выпуск производства по техкартам",
)
async def list_production(
    request: Request,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    org_unit_id: Annotated[UUID | None, Query()] = None,
) -> ProductionReportSchema:
    start, end = _period(date_from, date_to)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListProductionReportInteractor)
        items = await interactor(
            ProductionReportQuery(
                date_from=start, date_to=end, org_unit_id=org_unit_id
            )
        )

    return ProductionReportSchema(
        items=[ProductionReportRowSchema.from_dto(item) for item in items]
    )


@router.get(
    "/write-offs",
    response_model=WriteOffReportSchema,
    description="Списания по точкам и причинам",
)
async def list_write_offs(
    request: Request,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    org_unit_id: Annotated[UUID | None, Query()] = None,
) -> WriteOffReportSchema:
    start, end = _period(date_from, date_to)

    async with container(context={Request: request}) as context:
        interactor = await context.get(ListWriteOffReportInteractor)
        items = await interactor(
            WriteOffReportQuery(
                date_from=start, date_to=end, org_unit_id=org_unit_id
            )
        )

    return WriteOffReportSchema(
        items=[WriteOffReportRowSchema.from_dto(item) for item in items]
    )
