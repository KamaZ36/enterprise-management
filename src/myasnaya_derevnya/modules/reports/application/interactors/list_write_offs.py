from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.reports.application.dto import WriteOffReportRow
from myasnaya_derevnya.modules.reports.application.services.report_scope import (
    ReportScope,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.base import (
    ReportsReader,
)


@dataclass(frozen=True, slots=True)
class WriteOffReportQuery:
    date_from: date
    date_to: date
    org_unit_id: UUID | None = None


class ListWriteOffReportInteractor:
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
        self, query: WriteOffReportQuery
    ) -> list[WriteOffReportRow]:
        org_unit_ids = await self._report_scope.visible_org_unit_ids(
            query.org_unit_id
        )
        rows = await self._reader.write_offs(
            date_from=query.date_from,
            date_to=query.date_to,
            org_unit_ids=org_unit_ids,
        )
        titles = await self._business_api.org_unit_titles(
            {row.org_unit_id for row in rows}
        )

        return [
            replace(row, org_unit_name=titles.get(row.org_unit_id))
            for row in rows
        ]
