from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.reports.application.interactors.get_stock import (
    GetStockReportInteractor,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_summary import (
    GetSummaryInteractor,
)
from myasnaya_derevnya.modules.reports.application.interactors.get_turnover import (
    GetTurnoverReportInteractor,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_production import (
    ListProductionReportInteractor,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_sales import (
    ListSalesReportInteractor,
)
from myasnaya_derevnya.modules.reports.application.interactors.list_write_offs import (
    ListWriteOffReportInteractor,
)
from myasnaya_derevnya.modules.reports.application.services.report_scope import (
    ReportScope,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.base import (
    ReportsReader,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.sqlalchemy import (
    SQLAlchemyReportsReader,
)


class ReportsDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_reports_reader(self, session: AsyncSession) -> ReportsReader:
        return SQLAlchemyReportsReader(session)

    report_scope = provide(ReportScope, scope=Scope.REQUEST)

    summary_interactor = provide(GetSummaryInteractor, scope=Scope.REQUEST)
    sales_report_interactor = provide(
        ListSalesReportInteractor, scope=Scope.REQUEST
    )
    stock_report_interactor = provide(
        GetStockReportInteractor, scope=Scope.REQUEST
    )
    turnover_report_interactor = provide(
        GetTurnoverReportInteractor, scope=Scope.REQUEST
    )
    production_report_interactor = provide(
        ListProductionReportInteractor, scope=Scope.REQUEST
    )
    write_off_report_interactor = provide(
        ListWriteOffReportInteractor, scope=Scope.REQUEST
    )
