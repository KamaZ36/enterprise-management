from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.reports.application.dto import SalesReport
from myasnaya_derevnya.modules.reports.application.services.report_scope import (
    ReportScope,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.base import (
    ReportsReader,
)


@dataclass(frozen=True, slots=True)
class SalesReportQuery:
    date_from: date
    date_to: date
    org_unit_id: UUID | None = None


class ListSalesReportInteractor:
    def __init__(
        self,
        report_scope: ReportScope,
        reader: ReportsReader,
        business_api: BusinessAPI,
    ) -> None:
        self._report_scope = report_scope
        self._reader = reader
        self._business_api = business_api

    async def __call__(self, query: SalesReportQuery) -> SalesReport:
        org_unit_ids = await self._report_scope.visible_org_unit_ids(
            query.org_unit_id
        )
        rows = await self._reader.sales(
            date_from=query.date_from,
            date_to=query.date_to,
            org_unit_ids=org_unit_ids,
        )

        titles = await self._business_api.org_unit_titles(
            {row.org_unit_id for row in rows}
        )
        items = [
            replace(row, org_unit_name=titles.get(row.org_unit_id))
            for row in rows
        ]

        return SalesReport(
            items=items,
            total_revenue_kopecks=sum(row.revenue_kopecks for row in items),
            total_cost_kopecks=sum(row.cost_kopecks for row in items),
            total_margin_kopecks=sum(row.margin_kopecks for row in items),
            total_receipts=sum(row.receipts_count for row in items),
        )
