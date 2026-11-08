from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from myasnaya_derevnya.modules.reports.application.dto import (
    ReportSummary,
    SalesReportRow,
    StockReportRow,
    TurnoverReportRow,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_stock import (
    GetStockReportInteractor,
    StockReportQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_summary import (
    GetSummaryInteractor,
    SummaryQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_turnover import (
    GetTurnoverReportInteractor,
    TurnoverReportQuery,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_sales import (
    ListSalesReportInteractor,
    SalesReportQuery,
)

ORG_UNIT_ID = uuid4()


class FakeReportScope:
    def __init__(self, include_costs: bool) -> None:
        self.include_costs = include_costs

    async def visible_org_unit_ids(
        self, requested: UUID | None = None
    ) -> list[UUID] | None:
        return None

    async def can_see_costs(self) -> bool:
        return self.include_costs


class FakeBusinessAPI:
    async def org_unit_titles(self, unit_ids: set[UUID]) -> dict[UUID, str]:
        return {unit_id: "Точка" for unit_id in unit_ids}


class FakeReportsReader:
    async def stock(self, *, org_unit_ids):
        return [
            StockReportRow(
                org_unit_id=ORG_UNIT_ID,
                org_unit_name=None,
                positions=3,
                value_kopecks=1234500,
                expiring_lots=1,
            )
        ]

    async def sales(self, *, date_from, date_to, org_unit_ids):
        return [
            SalesReportRow(
                day=date(2026, 11, 8),
                org_unit_id=ORG_UNIT_ID,
                org_unit_name=None,
                revenue_kopecks=500000,
                cost_kopecks=300000,
                margin_kopecks=200000,
                receipts_count=4,
            )
        ]

    async def turnover(
        self, *, date_from, date_to, org_unit_ids, search=None
    ):
        return [
            TurnoverReportRow(
                org_unit_id=ORG_UNIT_ID,
                org_unit_name=None,
                nomenclature_id=uuid4(),
                nomenclature_name="Говядина",
                sku="BEEF",
                unit="kg",
                opening_quantity=Decimal(10),
                inbound_quantity=Decimal(5),
                outbound_quantity=Decimal(3),
                closing_quantity=Decimal(12),
                opening_value_kopecks=100000,
                inbound_value_kopecks=100000,
                outbound_value_kopecks=40000,
                closing_value_kopecks=160000,
            )
        ]

    async def summary(self, *, date_from, date_to, org_unit_ids):
        return ReportSummary(
            revenue_kopecks=500000,
            cost_kopecks=300000,
            margin_kopecks=200000,
            receipts_count=4,
            stock_value_kopecks=1234500,
            production_orders=2,
            write_off_cost_kopecks=50000,
            problem_receipts=0,
        )


async def test_stock_report_hides_value_without_cost_permission() -> None:
    interactor = GetStockReportInteractor(
        report_scope=FakeReportScope(include_costs=False),  # type: ignore[arg-type]
        reader=FakeReportsReader(),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(),  # type: ignore[arg-type]
    )

    rows = await interactor(StockReportQuery())

    assert rows[0].positions == 3
    assert rows[0].value_kopecks is None


async def test_stock_report_keeps_value_with_cost_permission() -> None:
    interactor = GetStockReportInteractor(
        report_scope=FakeReportScope(include_costs=True),  # type: ignore[arg-type]
        reader=FakeReportsReader(),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(),  # type: ignore[arg-type]
    )

    rows = await interactor(StockReportQuery())

    assert rows[0].value_kopecks == 1234500


async def test_sales_report_hides_cost_and_margin_without_permission() -> None:
    interactor = ListSalesReportInteractor(
        report_scope=FakeReportScope(include_costs=False),  # type: ignore[arg-type]
        reader=FakeReportsReader(),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(),  # type: ignore[arg-type]
    )

    report = await interactor(
        SalesReportQuery(date_from=date(2026, 11, 1), date_to=date(2026, 11, 8))
    )

    assert report.items[0].revenue_kopecks == 500000
    assert report.items[0].cost_kopecks is None
    assert report.items[0].margin_kopecks is None
    assert report.total_cost_kopecks is None
    assert report.total_margin_kopecks is None


async def test_summary_hides_money_values_without_permission() -> None:
    interactor = GetSummaryInteractor(
        report_scope=FakeReportScope(include_costs=False),  # type: ignore[arg-type]
        reader=FakeReportsReader(),  # type: ignore[arg-type]
    )

    summary = await interactor(
        SummaryQuery(date_from=date(2026, 11, 1), date_to=date(2026, 11, 8))
    )

    assert summary.revenue_kopecks == 500000
    assert summary.cost_kopecks is None
    assert summary.margin_kopecks is None
    assert summary.stock_value_kopecks is None
    assert summary.write_off_cost_kopecks is None
    assert summary.production_orders == 2


async def test_turnover_hides_values_without_permission() -> None:
    interactor = GetTurnoverReportInteractor(
        report_scope=FakeReportScope(include_costs=False),  # type: ignore[arg-type]
        reader=FakeReportsReader(),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(),  # type: ignore[arg-type]
    )

    rows = await interactor(
        TurnoverReportQuery(
            date_from=date(2026, 11, 1), date_to=date(2026, 11, 8)
        )
    )

    assert rows[0].opening_quantity == Decimal(10)
    assert rows[0].closing_quantity == Decimal(12)
    assert rows[0].opening_value_kopecks is None
    assert rows[0].closing_value_kopecks is None
