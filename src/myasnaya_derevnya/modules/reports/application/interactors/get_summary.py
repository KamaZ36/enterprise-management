from dataclasses import dataclass
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.reports.application.dto import ReportSummary
from myasnaya_derevnya.modules.reports.application.services.report_scope import (
    ReportScope,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.base import (
    ReportsReader,
)


@dataclass(frozen=True, slots=True)
class SummaryQuery:
    date_from: date
    date_to: date
    org_unit_id: UUID | None = None


class GetSummaryInteractor:
    def __init__(
        self,
        report_scope: ReportScope,
        reader: ReportsReader,
    ) -> None:
        self._report_scope = report_scope
        self._reader = reader

    async def __call__(self, query: SummaryQuery) -> ReportSummary:
        org_unit_ids = await self._report_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        return await self._reader.summary(
            date_from=query.date_from,
            date_to=query.date_to,
            org_unit_ids=org_unit_ids,
        )
