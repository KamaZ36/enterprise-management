from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.reports.application.dto import TurnoverReportRow
from myasnaya_derevnya.modules.reports.application.services.report_scope import (
    ReportScope,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.base import (
    ReportsReader,
)


@dataclass(frozen=True, slots=True)
class TurnoverReportQuery:
    date_from: date
    date_to: date
    org_unit_id: UUID | None = None
    search: str | None = None


class GetTurnoverReportInteractor:
    def __init__(
        self,
        report_scope: ReportScope,
        reader: ReportsReader,
        business_api: BusinessAPI,
    ) -> None:
        self._report_scope = report_scope
        self._reader = reader
        self._business_api = business_api

    async def __call__(
        self, query: TurnoverReportQuery
    ) -> list[TurnoverReportRow]:
        org_unit_ids = await self._report_scope.visible_org_unit_ids(
            query.org_unit_id
        )
        rows = await self._reader.turnover(
            date_from=query.date_from,
            date_to=query.date_to,
            org_unit_ids=org_unit_ids,
            search=query.search,
        )
        titles = await self._business_api.org_unit_titles(
            {row.org_unit_id for row in rows}
        )
        include_costs = await self._report_scope.can_see_costs()

        return [
            replace(
                row,
                org_unit_name=titles.get(row.org_unit_id),
                opening_value_kopecks=(
                    row.opening_value_kopecks if include_costs else None
                ),
                inbound_value_kopecks=(
                    row.inbound_value_kopecks if include_costs else None
                ),
                outbound_value_kopecks=(
                    row.outbound_value_kopecks if include_costs else None
                ),
                closing_value_kopecks=(
                    row.closing_value_kopecks if include_costs else None
                ),
            )
            for row in rows
        ]
